"""Can the plates actually be read?

Every other suite here asks whether a number is right. This asks whether a
reader can see it: whether a caption landed on the series it describes,
whether a value label ran off the canvas, whether two annotations stacked.
matplotlib reports none of that — it draws what it is told and the figure
is "fine".

It matters most in translation. A Spanish, Portuguese or French string is
routinely a third longer than the English it replaces, so the layout that
breaks is almost never the one anyone looked at. Fifty-two plates across
thirteen country-language pairs is well past what anyone checks by eye.

Two rules, because the four faults core.qa reports are not equally
decisive:

  OUTSIDE is a defect anywhere. Text past the edge of the canvas is not
  drawn, in any house style, for any reason. Every country is gated on it,
  and it found a real one: six American plates put the label of their
  right-hand axis off the page, so the reader never learned what that axis
  measured.

  The other three are judgement calls that differ by country. A note
  deliberately placed beside the line it explains is ONDATA by
  construction, and two countries' plates are built that way on purpose —
  France's tests require it. A value label resting just above its own axes
  box reads CLIPPED and prints fine. Rather than weaken the check until it
  says nothing, or rewrite four countries' plates to one country's
  conventions, each country's current count is recorded below and may not
  grow. New faults fail; the inherited ones are visible and countable.

A count carries SLACK, and only the count does. Every one of these faults
is decided by comparing two text bounding boxes against a tolerance of a
few pixels, and a bounding box is measured from the installed font build.
A Liberation Sans a hair wider on the CI image than on a laptop flips one
borderline annotation, which is how this first failed: four pages off by
exactly one, with nothing drawn differently. The slack absorbs that and
nothing else — a real regression moves a column of labels, not one — while
OUTSIDE, which is a fault at any tolerance, keeps its own gate at zero.
"""
from __future__ import annotations

import collections
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import pytest  # noqa: E402

from core import context, i18n, qa, style  # noqa: E402
from core.country import Country  # noqa: E402
from core.render import load_plates  # noqa: E402

BASELINE = Path(__file__).parent / "layout_baseline.json"
# Text off the canvas is never anyone's house style.
ALWAYS_FATAL = ("OUTSIDE",)
# How far a recorded count may drift before it counts as a regression. See
# the note in the module docstring: this is font-metric noise, not slack
# for new faults.
SLACK = 2


def faults(slug: str, lang: str) -> list[str]:
    """Render every plate of one country in one language and inspect it."""
    country = Country.load(slug)
    i18n.bind(country)
    i18n.set_lang(lang)
    found: list[str] = []
    real_save = style.Infographic.save

    def capture(self, path):
        self._draw_header()
        self._draw_footer()
        i18n.localize(self.fig)
        name = Path(str(path)).name
        found.extend(f"{name}  {f}" for f in qa.inspect(self.fig))
        plt.close(self.fig)
        return Path(path)

    style.Infographic.save = capture
    try:
        ctx = context.Context(country)
        for plate in load_plates(country):
            if plate.declarative:
                fig = ctx.fig(plate.title, plate.subtitle, source=plate.source)
                plate.draw(ctx, fig)
                fig.save(ctx.out(plate.filename))
            else:
                plate.draw(ctx)
    finally:
        style.Infographic.save = real_save
        i18n.set_lang("en")
        plt.close("all")
    return found


def _pairs():
    return [(c.slug, code) for c in Country.all() for code in c.locale_codes]


IDS = [f"{s}-{l}" for s, l in _pairs()]


@pytest.fixture(scope="session")
def baseline():
    return json.loads(BASELINE.read_text(encoding="utf-8")) \
        if BASELINE.exists() else {}


@pytest.mark.parametrize("slug,lang", _pairs(), ids=IDS)
def test_no_text_is_drawn_off_the_canvas(slug, lang, baseline):
    """The one fault no country is allowed to carry."""
    if not style.has_script_font(lang):
        pytest.skip(f"no installed font renders {lang}")
    bad = [f for f in faults(slug, lang)
           if any(k in f for k in ALWAYS_FATAL)]
    assert not bad, f"{slug}/{lang}:\n  " + "\n  ".join(bad[:10])


@pytest.mark.parametrize("slug,lang", _pairs(), ids=IDS)
def test_layout_faults_do_not_grow(slug, lang, baseline):
    """The inherited faults are counted, and the count may not rise.

    Run `python3 -m tests.layout_baseline` to re-record after a
    deliberate change; the diff then shows exactly what moved.
    """
    if not style.has_script_font(lang):
        pytest.skip(f"no installed font renders {lang}")
    counts = collections.Counter(f.split()[1] for f in faults(slug, lang))
    want = baseline.get(f"{slug}/{lang}", {})
    worse = {k: (v, want.get(k, 0)) for k, v in counts.items()
             if v > want.get(k, 0) + SLACK}
    assert not worse, (
        f"{slug}/{lang}: new layout faults (now vs recorded, slack "
        f"{SLACK}) {worse}. Fix them, or re-record the baseline if the "
        f"change was meant.")
