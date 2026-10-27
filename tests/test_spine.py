"""The plate spine, held: same chapter, same panels, same places, same scales.

PLATE_SPINE.md is the decision and core/spine.py its table. This checks
every country whose country.yaml says `spine: true` against that table by
drawing its plates and looking at the axes, and checks the table against
the site's list of topics. Countries not yet migrated are left alone; the
machinery is exercised here on a synthetic country built in a temporary
directory, so the checks are known to bite before the first real country
relies on them.
"""
from __future__ import annotations

import itertools
import math
import re
import textwrap
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402
import yaml  # noqa: E402

from core import context, i18n, rates, render, sitebuild, spine, style  # noqa: E402
from core.country import Country  # noqa: E402

TOL = 1e-6


# ----------------------------------------------------------- the checker
def drawn(country) -> list[tuple[render.Plate, style.Infographic, str]]:
    """Every plate of one country, composed in English and held, not written.

    Each entry is (plate, figure, stem of the file it would be saved as),
    the stem being what a chapter id names.
    """
    i18n.bind(country)
    i18n.set_lang("en")
    out = []
    current = {}
    real_save = style.Infographic.save

    def capture(self, path):
        self.compose()
        out.append((current["plate"], self, Path(str(path)).stem))
        return Path(path)

    style.Infographic.save = capture
    try:
        ctx = context.Context(country)
        for plate in render.load_plates(country):
            current["plate"] = plate
            render.draw(ctx, plate)
    finally:
        style.Infographic.save = real_save
    return out


def check_plate(ig: style.Infographic, cells: bool = True) -> list[str]:
    """What is wrong with one composed spine plate, or nothing.

    `cells` holds it to the cells the viewer finds its panels by; that only
    matters to a plate that has stories to open, so a country is held to it
    chapter by chapter as it writes them (see check_country).
    """
    where = f"{ig.country.slug}/{ig.topic}"
    if ig.topic is None:
        return [f"{ig.country.slug}: a plate with no topic"]
    bad = []
    fig = ig.fig
    w, h = fig.get_size_inches()
    if (round(w, 3), round(h, 3)) != spine.FRAME["figsize"]:
        bad.append(f"{where}: figure is {w}×{h}")
    if np.shape(ig.axes) != (spine.FRAME["nrows"], spine.FRAME["ncols"]):
        bad.append(f"{where}: grid is {np.shape(ig.axes)}")
    if abs(fig.subplotpars.right - spine.FRAME["right"]) > TOL:
        bad.append(f"{where}: right={fig.subplotpars.right}")
    if ig.country.tick_every != spine.TICK_EVERY:
        bad.append(f"{where}: tick_every={ig.country.tick_every}")

    for i, s in enumerate(spine.slots(ig.topic)):
        if i >= len(ig.axes_flat):
            break
        ax = ig.axes_flat[i]
        got = getattr(ax, "spine_slot", None)
        if got is None:
            if s.canonical:
                bad.append(f"{where}: slot {i + 1} should be {s.key}")
            elif ax.get_visible():
                bad.append(f"{where}: slot {i + 1} drawn but unclaimed")
            continue
        if got is not s or ax.get_gid() != s.key:
            bad.append(f"{where}: slot {i + 1} carries {ax.get_gid()!r}, "
                       f"the spine puts {s.key!r} there")
            continue
        if not s.canonical:
            continue
        lo, hi = ax.get_ylim()
        if s.scale == spine.LOG and ax.get_yscale() != "log":
            bad.append(f"{where}: {s.key} is not on a log axis")
        if s.scale == spine.LINEAR and ax.get_yscale() != "linear":
            bad.append(f"{where}: {s.key} should be linear")
        rlo, rhi = s.ref
        on_ref = math.isclose(lo, rlo, abs_tol=TOL) and \
            math.isclose(hi, rhi, abs_tol=TOL)
        if not on_ref:
            bad.append(f"{where}: {s.key} drawn on ({lo:g}, {hi:g}), not "
                       f"its shared comparison scale {s.ref}")
        if getattr(ax, "spine_extended", False):
            bad.append(f"{where}: {s.key} has a country-local extension")

    if cells:
        bad += cell_faults(ig)

    # Across every axes on the plate, twins and lenses included: nothing
    # inverted and nothing clipped.
    for ax in fig.axes:
        if not ax.get_visible():
            continue
        name = ax.get_gid() or ax.get_title(loc="left") or "an axes"
        lo, hi = ax.get_ylim()
        if lo > hi:
            bad.append(f"{where}: {name} has an inverted y-axis")
            lo, hi = hi, lo
        ext = spine.data_extent(ax)
        if ext and (ext[0] < lo - TOL * max(1, abs(lo))
                    or ext[1] > hi + TOL * max(1, abs(hi))):
            bad.append(f"{where}: {name} clips its data: {ext} outside "
                       f"({lo:g}, {hi:g})")
    return bad


def cell_faults(ig: style.Infographic) -> list[str]:
    """Panels that draw outside the cell the spine says they occupy.

    The viewer finds the panel under a click from `spine.panel_cell`, which
    repeats the margins this figure was built with. A panel whose title,
    ticks or labels spill out of its cell would answer to its neighbour, and
    a margin changed in one place and not the other would do it to all of
    them, so every spine plate is held to its cells here.
    """
    where = f"{ig.country.slug}/{ig.topic}"
    renderer = ig.fig.canvas.get_renderer()
    to_figure = ig.fig.transFigure.inverted()
    bad = []
    for i, ax in enumerate(ig.axes_flat):
        if not ax.get_visible():
            continue
        left, top, width, height = spine.panel_cell(i)
        x0, y0, x1, y1 = left, 1 - top - height, left + width, 1 - top
        with warnings.catch_warnings():
            # Measuring draws the tick labels for the first time, and a
            # signed axis asks the font for a minus sign it may not have.
            # The plate is written through the same font, so this says
            # nothing about the layout being checked.
            warnings.filterwarnings("ignore", message="Glyph 8722")
            ink = ax.get_tightbbox(renderer).transformed(to_figure)
        if (ink.x0 < x0 - TOL or ink.x1 > x1 + TOL
                or ink.y0 < y0 - TOL or ink.y1 > y1 + TOL):
            bad.append(f"{where}: panel {i + 1} draws "
                       f"({ink.x0:.3f}, {ink.y0:.3f})–({ink.x1:.3f}, "
                       f"{ink.y1:.3f}) outside its cell "
                       f"({x0:.3f}, {y0:.3f})–({x1:.3f}, {y1:.3f})")
    return bad


def check_country(country) -> list[str]:
    """Everything test_spine holds a spine country to, as a list of faults."""
    try:
        plates = drawn(country)
        bad = []
        if country.tick_every != spine.TICK_EVERY:
            bad.append(f"{country.slug}: tick_every is "
                       f"{country.tick_every}, the spine labels every "
                       f"{spine.TICK_EVERY}")
        by_stem = {stem: ig for _, ig, stem in plates}
        for ch in sitebuild.chapters_for(country):
            ig = by_stem.get(ch["id"])
            if ig is None:
                bad.append(f"{country.slug}: chapter {ch['id']} has no plate "
                           f"saved as {ch['id']}.png")
            elif ig.topic != ch.get("topic"):
                bad.append(f"{country.slug}: chapter {ch['id']} is topic "
                           f"{ch.get('topic')!r}, its plate declares "
                           f"{ig.topic!r}")
        told = {ch["id"] for ch in sitebuild.chapters_for(country)
                if ch.get("stories")}
        for _, ig, stem in plates:
            bad += check_plate(ig, cells=stem in told)
        return bad
    finally:
        plt.close("all")


# ------------------------------------------------------- the real countries
SPINE_COUNTRIES = [c for c in Country.all() if c.spine]


@pytest.mark.parametrize("spine_country", SPINE_COUNTRIES,
                         ids=[c.slug for c in SPINE_COUNTRIES])
def test_a_spine_country_keeps_to_the_spine(spine_country):
    bad = check_country(spine_country)
    assert not bad, f"{spine_country.slug}:\n  " + "\n  ".join(bad[:20])


@pytest.mark.parametrize("spine_country", SPINE_COUNTRIES,
                         ids=[c.slug for c in SPINE_COUNTRIES])
def test_a_spine_country_can_say_the_spine_in_its_languages(spine_country):
    """The shared units and the marker are English until a catalog says
    otherwise; a spine country carries every one of them."""
    import json
    path = spine_country.dir / "i18n.json"
    cat = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    gaps = [f"{s!r}/{code}" for s in spine.strings()
            for code in spine_country.locale_codes
            if code != "en" and not (cat.get(s) or {}).get(code)]
    assert not gaps, f"{spine_country.slug}: untranslated " + ", ".join(gaps)


def test_comparison_peers_use_identical_canonical_axes():
    """The viewer wipes finished SVG pixels; every transform must register."""
    signatures = {}
    owners = {}
    try:
        for country in SPINE_COUNTRIES:
            for _, ig, _ in drawn(country):
                for ax in ig.axes_flat:
                    s = getattr(ax, "spine_slot", None)
                    if s is None or not s.canonical:
                        continue
                    assert getattr(ax, "spine_unit", None) == s.unit
                    assert ax.get_ylabel() == s.unit, \
                        f"{country.slug}/{s.key}: {ax.get_ylabel()!r} != {s.unit!r}"
                    sig = (
                        tuple(round(v, 9) for v in ax.get_position().bounds),
                        ax.get_xscale(), ax.get_yscale(),
                        tuple(round(v, 9) for v in ax.get_xlim()),
                        tuple(round(v, 9) for v in ax.get_ylim()),
                        tuple(round(float(v), 9) for v in ax.get_xticks()),
                        tuple(round(float(v), 9) for v in ax.get_yticks()),
                        s.unit,
                    )
                    if s.key in signatures:
                        assert sig == signatures[s.key], (
                            f"{country.slug}/{s.key} does not register with "
                            f"{owners[s.key]}: {sig} != {signatures[s.key]}")
                    else:
                        signatures[s.key] = sig
                        owners[s.key] = country.slug
            plt.close("all")
    finally:
        plt.close("all")


# ---------------------------------------------------------- the table
def test_the_spine_has_the_sites_topics():
    from tests.test_site import SPINE as SITE_SPINE
    assert set(spine.SPINE) == SITE_SPINE


def test_the_spine_table_is_well_formed():
    seen = set()
    for topic, slots in spine.SPINE.items():
        assert len(slots) == spine.FRAME["nrows"] * spine.FRAME["ncols"], topic
        lens_seen = False
        for s in slots:
            assert s.key.startswith(topic + "."), s.key
            assert s.key not in seen, s.key
            seen.add(s.key)
            assert s.kind in (spine.CANONICAL, spine.LENS), s.key
            assert s.grow in (spine.UP, spine.DOWN, spine.BOTH, spine.NONE)
            assert s.scale in (spine.LINEAR, spine.LOG), s.key
            if s.canonical:
                assert not lens_seen, f"{s.key}: canonical after a lens slot"
                assert s.unit, f"{s.key}: no unit"
                lo, hi = s.ref
                assert lo < hi, s.key
                if s.zero:
                    assert lo < 0 < hi, f"{s.key}: zero line off the range"
            else:
                lens_seen = True
                assert s.ref is None and s.scale == spine.LINEAR, s.key
            if s.scale == spine.LOG:
                assert s.ref[0] > 0 and s.ticks, s.key
                assert list(s.ticks) == sorted(s.ticks), s.key
                assert s.ticks[0] >= s.ref[0] and s.ticks[-1] <= s.ref[1]
            else:
                assert not s.ticks, s.key


def test_a_log_axis_uses_the_declared_ladder():
    s = spine.SLOTS["markets.currency"]
    assert spine.log_ticks(s, *s.ref) == list(s.ticks)
    assert spine.tick_label(0.5) == "0.5"
    assert spine.tick_label(50_000) == "50,000"


def test_data_outside_a_shared_scale_fail_loudly():
    s = spine.SLOTS["economy.growth"]
    with pytest.raises(spine.SpineError, match="atlas-wide range"):
        spine.fit(s, (-40, 5))
    assert spine.fit(s, (-3, 5)) == (s.ref, False)


def test_a_log_slot_refuses_a_value_it_cannot_draw():
    with pytest.raises(spine.SpineError):
        spine.fit(spine.SLOTS["world.gdp"], (0, 100))


# ---------------------------------------------------- a synthetic country
_COUNTER = itertools.count()

YAML = dict(
    flag_emoji="🏳", name={"en": "Synthland"},
    locales=[{"code": "en", "endonym": "English"}], default_locale="en",
    years={"from": 2006, "to": 2026}, last_full_year=2025, tick_every=2,
    bands=[{"from": 2008.5, "to": 2009.5, "label": "slump"}],
    currency={"code": "USD"},
    palette={"ink": "#111111", "muted": "#555555", "faint": "#999999",
             "paper": "#FBFAF7", "card": "#FFFFFF", "grid": "#E7E4DD",
             "spine": "#C9C6BE", "band": "#EFECE5", "primary": "#225588",
             "alert": "#AA2222",
             "series": ["#225588", "#AA2222", "#228844"],
             "flag_bands": ["#225588", "#FFFFFF", "#AA2222"]},
    seo={"title": {"en": "t"}, "description": {"en": "d"},
         "keywords": ["k"], "spatial": "Synthland"},
    spine=True,
)

# A function plate (economy) and a declarative one (security), both on
# the spine. GROWTH_2020 and the others are rewritten by the tests below.
PLATES = '''
Y = list(range(2006, 2027))
GROWTH_2020 = -8.0
HOMICIDE = 2.0
TOPIC = "security"
ORDER = ("security.homicide", "security.suicide",
         "security.road_deaths", "security.lens")
INVERT = False


def plate_economy(ctx):
    ig = ctx.fig("Economy", "sub", topic="economy")
    ax = ig.slot("economy.growth", "Real GDP growth")
    g = [GROWTH_2020 if y == 2020 else 2.0 for y in Y]
    ctx.bars(ax, Y, g, lambda v: ctx.p.primary)
    ig.add_recessions(ax)
    ax = ig.slot("economy.gdp_per_person", "GDP per person")
    ctx.line(ax, Y, [20_000 + 500 * i for i in range(len(Y))], ctx.p.ink)
    ax = ig.slot("economy.inflation", "Inflation")
    ctx.pending(ax)
    ax = ig.slot("economy.unemployment", "Unemployment")
    ctx.line(ax, Y, [8.0] * len(Y), ctx.p.ink)
    for a in ig.axes_flat:
        ig.style_axis(a)
    ig.save(ctx.out("01-economy.png"))


def plate_security(ctx, ig):
    for key in ORDER:
        ax = ig.slot(key, key)
        if key == "security.homicide":
            ctx.line(ax, Y, [HOMICIDE] * len(Y), ctx.p.ink)
        elif key == "security.lens":
            ctx.line(ax, Y, list(range(len(Y))), ctx.p.ink)
            if INVERT:
                ax.invert_yaxis()
        else:
            ctx.line(ax, Y, [5.0] * len(Y), ctx.p.ink)
    for a in ig.axes_flat:
        ig.style_axis(a)


PLATES = (
    ("plate_economy", plate_economy),
    dict(id="02", slug="security", builder=plate_security, topic=TOPIC,
         title="Security", subtitle="sub", alt="alt"),
)
'''

CHAPTERS = '''
def build(ctx):
    return [
        {"id": "01-economy", "topic": "economy", "n": "01",
         "family": "money", "title": {"en": "Economy"}},
        {"id": "02-security", "topic": "security", "n": "02",
         "family": "people", "title": {"en": "Security"}},
    ]
'''


def synthetic(tmp_path, plates_extra: str = "", chapters: str = CHAPTERS,
              **cfg) -> Country:
    """A throwaway spine country; `plates_extra` overrides PLATES' knobs."""
    slug = f"synth{next(_COUNTER)}"
    d = tmp_path / slug
    (d / "data").mkdir(parents=True)
    conf = {**YAML, "slug": slug, **cfg}
    (d / "country.yaml").write_text(yaml.safe_dump(conf, allow_unicode=True),
                                    encoding="utf-8")
    body = PLATES.replace("\nPLATES = (", textwrap.dedent(plates_extra)
                          + "\nPLATES = (", 1)
    (d / "plates.py").write_text(body, encoding="utf-8")
    (d / "chapters.py").write_text(chapters, encoding="utf-8")
    return Country.from_dir(d)


def _plate(country, topic):
    for _, ig, _ in drawn(country):
        if ig.topic == topic:
            return ig
    raise AssertionError(f"no {topic} plate")


def test_a_synthetic_spine_country_passes(tmp_path):
    c = synthetic(tmp_path)
    assert c.spine
    assert check_country(c) == []


def test_data_past_the_shared_scale_fail_the_render(tmp_path):
    c = synthetic(tmp_path, "GROWTH_2020 = -21.0\nHOMICIDE = 300.0\n")
    with pytest.raises(spine.SpineError, match="shared comparison scale"):
        check_country(c)
    plt.close("all")


def test_a_pending_slot_inherits_the_shared_axis(tmp_path):
    c = synthetic(tmp_path)
    try:
        ax = _plate(c, "economy").axes_flat[2]
        s = spine.SLOTS["economy.inflation"]
        assert ax.spine_pending
        assert ax.get_yscale() == s.scale
        assert ax.get_ylim() == s.ref
        assert not ax.spine_extended
    finally:
        plt.close("all")


def test_a_slot_claimed_out_of_order_fails_loudly(tmp_path):
    c = synthetic(tmp_path, '''
        ORDER = ("security.suicide", "security.homicide",
                 "security.road_deaths", "security.lens")
    ''')
    with pytest.raises(spine.SpineError, match="claimed before"):
        check_country(c)


def test_a_missing_canonical_slot_fails_at_save(tmp_path):
    c = synthetic(tmp_path, '''
        ORDER = ("security.homicide", "security.suicide")
    ''')
    with pytest.raises(spine.SpineError, match="never claimed"):
        check_country(c)


def test_a_lens_slot_may_be_left_out(tmp_path):
    c = synthetic(tmp_path, '''
        ORDER = ("security.homicide", "security.suicide",
                 "security.road_deaths")
    ''')
    try:
        assert not _plate(c, "security").axes_flat[3].get_visible()
    finally:
        plt.close("all")
    assert check_country(c) == []


def test_a_slot_from_another_topic_is_refused(tmp_path):
    c = synthetic(tmp_path, '''
        ORDER = ("economy.growth",)
    ''')
    with pytest.raises(spine.SpineError, match="not one of this topic"):
        check_country(c)


def test_an_inverted_axis_is_caught(tmp_path):
    c = synthetic(tmp_path, "INVERT = True\n")
    assert any("inverted" in b for b in check_country(c))


def test_a_chapter_on_another_topic_is_caught(tmp_path):
    c = synthetic(tmp_path, chapters=CHAPTERS.replace(
        '"topic": "security"', '"topic": "mortality"'))
    assert any("declares 'security'" in b for b in check_country(c))


def test_a_chapter_without_a_plate_is_caught(tmp_path):
    c = synthetic(tmp_path, chapters=CHAPTERS.replace(
        '"02-security"', '"03-security"'))
    assert any("no plate" in b for b in check_country(c))


def test_a_plate_without_a_topic_is_caught(tmp_path):
    c = synthetic(tmp_path, 'TOPIC = None\nORDER = ()\n')
    assert any("no topic" in b for b in check_country(c))


def test_the_frame_is_fixed_for_a_topic(tmp_path):
    c = synthetic(tmp_path)
    ctx = context.Context(c)
    for kw in ({"ncols": 3}, {"figsize": (18.0, 10.2)}, {"right": 0.975}):
        with pytest.raises(spine.SpineError, match="drawn on"):
            ctx.fig("t", "s", topic="economy", **kw)
    plt.close("all")


def test_a_spine_plate_labels_every_second_year(tmp_path):
    c = synthetic(tmp_path, tick_every=3)
    with pytest.raises(spine.SpineError, match="tick_every"):
        context.Context(c).fig("t", "s", topic="economy")
    plt.close("all")


def test_next_panel_is_refused_on_a_spine_plate(tmp_path):
    ig = context.Context(synthetic(tmp_path)).fig("t", "s", topic="economy")
    with pytest.raises(spine.SpineError, match="slot"):
        ig.next_panel("x")
    plt.close("all")


def test_the_panel_cells_tile_the_plate_in_reading_order():
    cells = [spine.panel_cell(i) for i in range(4)]
    for left, top, width, height in cells:
        assert width > 0 and height > 0
        assert left >= 0 and top >= 0
        assert left + width <= 1 + TOL and top + height <= 1 + TOL
    for a, b in itertools.combinations(cells, 2):
        apart_x = a[0] + a[2] <= b[0] + TOL or b[0] + b[2] <= a[0] + TOL
        apart_y = a[1] + a[3] <= b[1] + TOL or b[1] + b[3] <= a[1] + TOL
        assert apart_x or apart_y, f"{a} overlaps {b}"
    # 1 top-left, 2 top-right, 3 bottom-left, 4 bottom-right: each row sits
    # above the next and each left panel left of its right-hand neighbour.
    for left, right in ((0, 1), (2, 3)):
        assert cells[left][0] + cells[left][2] <= cells[right][0] + TOL
    for upper, lower in ((0, 2), (1, 3)):
        assert cells[upper][1] + cells[upper][3] <= cells[lower][1] + TOL


def test_the_four_cells_are_the_same_size():
    """So the panels lift, and are isolated, at one size."""
    sizes = {(round(c[2], 4), round(c[3], 4))
             for c in (spine.panel_cell(i) for i in range(4))}
    assert len(sizes) == 1, sizes


def test_a_cell_exists_only_for_the_four_panels():
    for bad in (-1, 4):
        with pytest.raises(IndexError):
            spine.panel_cell(bad)


def test_a_panel_that_leaves_its_cell_is_caught(tmp_path):
    """The check is known to bite: move the margins and it says so."""
    c = synthetic(tmp_path)
    try:
        ig = _plate(c, "security")
        assert cell_faults(ig) == []
        ig.fig.subplots_adjust(left=0.30)
        assert any("outside its cell" in b for b in cell_faults(ig))
    finally:
        plt.close("all")


def test_a_plate_off_the_spine_is_untouched(tmp_path):
    """Unmigrated plates keep next_panel, any grid and their own limits."""
    ig = context.Context(synthetic(tmp_path)).fig("t", "s", ncols=3)
    ax = ig.next_panel("x")
    ax.plot([2006, 2007], [5, 6])
    ax.set_ylim(4, 7)
    ig.apply_spine()
    assert ax.get_ylim() == (4, 7)
    assert ig.fig.subplotpars.right == pytest.approx(0.955)
    plt.close("all")


def test_svg_output_has_no_trailing_horizontal_whitespace(tmp_path):
    c = synthetic(tmp_path)
    i18n.bind(c)
    i18n.set_lang("en")
    ig = context.Context(c).fig("t", "s")
    ax = ig.next_panel("x")
    ax.plot([2006, 2007], [5, 6], marker="o")
    out = tmp_path / "plate.png"
    ig.save(out)
    raw = out.with_suffix(".svg").read_bytes()
    assert not re.search(rb"[ \t]+(?=\r?$)", raw, flags=re.MULTILINE)


# ------------------------------------------------------------------ rates
def test_a_rate_is_aligned_by_year_not_by_position():
    count = ([2012, 2010, 2011], [30, 10, 20])
    pop = {2006: 1, 2010: 1_000_000, 2011: 2_000_000, 2012: 3_000_000}
    years, vals = rates.per_100k(count, pop)
    assert years == [2010, 2011, 2012]
    assert vals == pytest.approx([1.0, 1.0, 1.0])
    assert rates.per_1000([(2010, 5)], pop) == ([2010], [pytest.approx(0.005)])


def test_a_rate_without_its_years_population_raises():
    with pytest.raises(ValueError, match="2011"):
        rates.per_100k({2010: 1, 2011: 2}, {2010: 100, 2012: 100})
    with pytest.raises(ValueError, match="2011"):
        rates.per_1000({2010: 1, 2011: 2}, {2010: 100, 2011: float("nan")})


def test_a_blank_count_is_dropped_not_zeroed():
    years, _ = rates.per_100k({2010: float("nan"), 2011: 2},
                              {2011: 100})
    assert years == [2011]


def test_index_2006():
    years, vals = rates.index_2006({2006: 50, 2007: 75, 2005: 25})
    assert years == [2005, 2006, 2007]
    assert vals == pytest.approx([50, 100, 150])
    with pytest.raises(ValueError, match="2006"):
        rates.index_2006({2007: 1})


def test_fx_index_rises_when_the_currency_strengthens():
    # 2 units per US$ in 2006; 4 per US$ later is a currency at half its
    # 2006 value, 1 per US$ is one worth twice as much.
    years, vals = rates.fx_index({2006: 2.0, 2010: 4.0, 2020: 1.0})
    assert years == [2006, 2010, 2020]
    assert vals == pytest.approx([100, 50, 200])
    with pytest.raises(ValueError):
        rates.fx_index({2006: 2.0, 2010: 0.0})
