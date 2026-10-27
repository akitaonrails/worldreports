"""The stories a chapter tells about its panels.

A story is the plain-language reading of one panel, opened from the viewer.
It is editorial copy like a card's blurb, so it follows the same rules: every
locale the country publishes is written, and every number in it is read from
the country's CSVs at build time, in that locale's number style, so a story
and the plate it explains cannot disagree after a refetch.
"""
from __future__ import annotations

import pytest

from core import sitebuild, spine
from core.country import Country

PAIRS = [(2019, 1.3), (2020, -3.3), (2021, 4.8), (2022, 3.0)]


@pytest.fixture(scope="module")
def ctx():
    return sitebuild.SiteContext(Country.load("brasil"))


def test_a_fact_is_written_in_each_locales_number_style(ctx):
    fact = ctx.fact([(2025, 10686.0)], "count")
    assert fact["value"]["en"] == "10,686"
    assert fact["value"]["pt"] == "10.686"
    assert fact["year"] == 2025


def test_a_fact_can_name_the_year_it_reads(ctx):
    assert ctx.fact(PAIRS, "pct_s", year=2020)["year"] == 2020
    assert ctx.fact(PAIRS, "pct_s", year=2020)["value"]["en"] == "-3.3%"


def test_a_fact_stops_at_the_last_full_year_unless_it_is_a_level(ctx):
    pairs = [(2025, 2.3), (2026, 9.9)]
    assert ctx.fact(pairs, "pct")["year"] == ctx.LAST_FULL_YEAR
    assert ctx.fact(pairs, "pct", kind="level")["year"] == 2026


def test_a_fact_with_no_data_is_an_error_not_a_blank(ctx):
    with pytest.raises(KeyError, match="no value"):
        ctx.fact(PAIRS, "pct", year=1999)


def _beat(ctx, head="h", text="x"):
    return (ctx.text(en=head, pt=head), ctx.text(en=text, pt=text))


def _told(ctx, beats=None, **kw):
    """A story of three plain beats unless told otherwise."""
    beats = beats or [_beat(ctx), _beat(ctx), _beat(ctx)]
    return ctx.story(title=ctx.text(en="Slump", pt="Tombo"), beats=beats, **kw)


def test_a_story_fills_its_numbers_and_years_per_locale(ctx):
    story = _told(
        ctx, beats=[_beat(ctx), (ctx.text(en="The fall", pt="A queda"),
                                 ctx.text(en="Output fell {drop} in {drop_year}.",
                                          pt="A produção caiu {drop} em {drop_year}.")),
                    _beat(ctx)],
        facts={"drop": ctx.fact(PAIRS, "pct_s", year=2020)})
    assert story["en"]["title"] == "Slump"
    assert story["en"]["beats"][1] == {"head": "The fall",
                                       "text": "Output fell -3.3% in 2020."}
    assert story["pt"]["beats"][1]["text"] == "A produção caiu -3,3% em 2020."
    assert set(story["en"]) == {"title", "beats"}


def test_a_story_is_a_few_short_beats_not_a_wall_or_a_stub(ctx):
    with pytest.raises(ValueError, match="beats"):
        _told(ctx, beats=[_beat(ctx), _beat(ctx)])
    with pytest.raises(ValueError, match="beats"):
        _told(ctx, beats=[_beat(ctx)] * 7)


def test_a_story_must_be_written_in_every_locale(ctx):
    with pytest.raises(KeyError, match="missing"):
        _told(ctx, beats=[_beat(ctx), _beat(ctx),
                          (ctx.text(en="h", pt="h"), {"en": "b"})])


def test_a_placeholder_with_no_fact_fails_the_build(ctx):
    with pytest.raises(KeyError, match="no fact"):
        _told(ctx, beats=[_beat(ctx), _beat(ctx),
                          _beat(ctx, text="{ghost}")])


def test_a_fact_the_story_never_uses_fails_the_build(ctx):
    """An unused fact is a sentence that was reworded away from its number."""
    with pytest.raises(KeyError, match="never used"):
        _told(ctx, facts={"stale": ctx.fact(PAIRS, "pct", year=2020)})


def test_a_fact_in_a_title_or_a_head_counts_as_used(ctx):
    story = ctx.story(
        title=ctx.text(en="Down {drop}", pt="Queda de {drop}"),
        beats=[_beat(ctx), _beat(ctx, head="In {drop_year}"), _beat(ctx)],
        facts={"drop": ctx.fact(PAIRS, "pct", year=2020)})
    assert story["pt"]["title"] == "Queda de -3,3%"
    assert story["en"]["beats"][1]["head"] == "In 2020"


def test_every_story_belongs_to_a_panel_of_its_chapters_topic(country):
    for ch in sitebuild.chapters_for(country):
        stories = ch.get("stories") or {}
        keys = {s.key for s in spine.slots(ch["topic"])} if stories else set()
        stray = sorted(set(stories) - keys)
        assert not stray, f"{country.slug}/{ch['id']}: {stray} are not " \
                          f"panels of {ch['topic']!r}"


def test_every_story_is_told_in_every_locale_with_nothing_unfilled(country):
    for ch in sitebuild.chapters_for(country):
        for key, story in (ch.get("stories") or {}).items():
            for loc in country.locale_codes:
                told = story[loc]
                texts = [("title", told["title"])]
                for i, beat in enumerate(told["beats"]):
                    texts += [(f"beat{i}/head", beat["head"]),
                              (f"beat{i}/text", beat["text"])]
                for field, text in texts:
                    where = f"{country.slug}/{key}/{loc}/{field}"
                    assert text.strip(), f"{where}: empty"
                    assert "{" not in text, f"{where}: unfilled: {text}"
