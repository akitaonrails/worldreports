"""Render a country's plates without writing them, and look inside.

This is the harness behind every `countries/<slug>/tests/test_plates.py`.
Those tests ask whether each line on a plate means what its label says —
the one question geometry cannot answer. A panel whose two series are
labelled the wrong way round is perfectly clean to anything measuring
pixels, and exactly backwards to a reader. That happened: an S&P 500
converted *into* reais was labelled "(USD)" and the native dollar index
"(in BRL)", which inverted the panel's whole point, and it was caught by
eye months later.

So each of those tests states a relationship that must hold between a
label and the numbers drawn under it, and swapping two labels fails the
build.
"""
from __future__ import annotations

import functools
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# A country has up to eleven plates and the tests want all of them at once,
# because the figure is the thing under test and closing it would leave
# nothing to inspect. matplotlib warns at twenty open figures on the
# assumption that holding them is a leak; here it is the design.
matplotlib.rcParams["figure.max_open_warning"] = 0

from core import context, i18n, style  # noqa: E402
from core.country import Country  # noqa: E402
from core.render import load_plates  # noqa: E402


class Panel:
    """One axes, asked about rather than measured."""

    def __init__(self, ax):
        self.ax = ax

    @property
    def title(self) -> str:
        return self.ax.get_title(loc="left")

    def data_lines(self):
        """Only the lines drawn in data coordinates.

        axhline and axvline live in a blended transform where one axis is
        a fraction of the panel, so comparing their values against
        anything real is meaningless.
        """
        return [ln for ln in self.ax.get_lines()
                if ln.get_transform() is self.ax.transData]

    def lines(self) -> dict[str, list[float]]:
        """{legend label: y values} for the lines that carry a label.

        matplotlib names an unlabelled artist "_child0", so anything
        starting with an underscore is a line nobody meant to name.
        """
        out = {}
        for ln in self.ax.get_lines():
            label = ln.get_label()
            if label and not label.startswith("_"):
                out[label] = [float(v) for v in ln.get_ydata()]
        return out

    def series(self, needle: str) -> list[float]:
        """The one labelled line whose label contains `needle`."""
        hits = {k: v for k, v in self.lines().items()
                if needle.lower() in k.lower()}
        assert hits, (f"no line labelled like {needle!r} on {self.title!r}; "
                      f"have {sorted(self.lines())}")
        assert len(hits) == 1, f"{needle!r} matches {sorted(hits)}"
        return next(iter(hits.values()))

    def points(self, needle: str) -> dict[float, float]:
        """{x: y} for the one labelled line whose label contains `needle`."""
        for ln in self.data_lines():
            label = ln.get_label()
            if label.startswith("_") or needle.lower() not in label.lower():
                continue
            return {float(x): float(y)
                    for x, y in zip(ln.get_xdata(), ln.get_ydata())
                    if float(y) == float(y)}
        raise AssertionError(
            f"no line labelled like {needle!r} on {self.title!r}; "
            f"have {sorted(self.lines())}")

    def paired(self, a: str, b: str) -> list[tuple[float, float, float]]:
        """(x, a, b) for the years both series actually cover.

        Two series on one panel rarely span the same years — a modelled
        estimate may start seven years after the registered count it
        corrects. Zipping their value arrays then compares 2013 against
        2006 and the comparison means nothing, which is exactly how a
        containment test can pass or fail for the wrong reason.
        """
        left, right = self.points(a), self.points(b)
        shared = sorted(set(left) & set(right))
        return [(x, left[x], right[x]) for x in shared]

    def bars(self) -> list[float]:
        """Bar heights, in data coordinates.

        Only the patches drawn in data space: a recession band is an
        axvspan whose height is 1.0 in axes fraction, and counting it as a
        bar of height 1 would compare an axis fraction against a Gini
        coefficient.
        """
        return [float(p.get_height()) for p in self.ax.patches
                if p.get_transform() is self.ax.transData
                and hasattr(p, "get_height")]

    def texts(self) -> list[str]:
        return [t.get_text() for t in self.ax.texts if t.get_text().strip()]

    def legend_labels(self) -> list[str]:
        leg = self.ax.get_legend()
        return [t.get_text() for t in leg.get_texts()] if leg else []

    def ylim(self):
        return self.ax.get_ylim()

    def nothing_is_clipped(self, slack: float = 0.0):
        """Every plotted point sits inside the axes it is drawn on.

        A series that runs off the top is not an error anywhere in
        matplotlib; it is simply invisible, and the panel then shows a
        shape the data does not have.
        """
        # sorted, because an axis where lower is better is drawn inverted
        lo, hi = sorted(self.ylim())
        out = []
        for ln in self.data_lines():
            label = ln.get_label()
            for y in ln.get_ydata():
                y = float(y)
                if y != y:            # NaN: a year the publisher left blank
                    continue
                if y < lo - slack or y > hi + slack:
                    out.append(f"{label}: {y} outside [{lo}, {hi}]")
        for h in self.bars():
            if h != h:
                continue
            if h < min(lo, 0) - slack or h > hi + slack:
                out.append(f"bar {h} outside [{lo}, {hi}]")
        assert not out, f"{self.title!r} clips: " + "; ".join(out[:4])


class Plate:
    """One rendered figure, addressed by panel title."""

    def __init__(self, name: str, fig):
        self.name = name
        self.fig = fig

    def panel(self, needle: str) -> Panel:
        for ax in self.fig.axes:
            if needle.lower() in ax.get_title(loc="left").lower():
                return Panel(ax)
        titles = [ax.get_title(loc="left") for ax in self.fig.axes]
        raise AssertionError(
            f"{self.name}: no panel titled like {needle!r}; have {titles}")

    def panels(self) -> list[Panel]:
        return [Panel(ax) for ax in self.fig.axes]

    def texts(self) -> list[str]:
        """Every string on the figure, panels included."""
        import matplotlib.text as mtext
        return [t.get_text() for t in self.fig.findobj(match=mtext.Text)
                if t.get_text().strip()]


@functools.lru_cache(maxsize=None)
def _render(slug: str, lang: str) -> dict:
    """Draw every plate of one country, keeping the figures in memory.

    `Infographic.save` is replaced rather than redirected to a temporary
    directory: the figures are what the tests look at, and closing them
    on the way out would leave nothing to look at. Cached because a plate
    costs about a second to draw and a country's tests want all of them.
    """
    country = Country.load(slug)
    i18n.bind(country)
    i18n.set_lang(lang)
    captured: dict[str, object] = {}
    current = {"name": ""}
    real_save = style.Infographic.save

    def capture(self, path):
        self._draw_header()
        self._draw_footer()
        i18n.localize(self.fig)
        captured[current["name"]] = self.fig
        return Path(path)

    style.Infographic.save = capture
    try:
        ctx = context.Context(country)
        for plate in load_plates(country):
            current["name"] = plate.name
            if plate.declarative:
                fig = ctx.fig(plate.title, plate.subtitle, source=plate.source)
                plate.draw(ctx, fig)
                fig.save(ctx.out(plate.filename))
            else:
                plate.draw(ctx)
    finally:
        style.Infographic.save = real_save
        i18n.set_lang("en")
    return captured


def plate(slug: str, name: str, lang: str = "en") -> Plate:
    """One plate of one country, drawn and held for inspection.

    `name` is the plate's function name, as countries/<slug>/plates.py
    lists it in PLATES.
    """
    figures = _render(slug, lang)
    assert name in figures, \
        f"{slug}: no plate named {name!r}; have {sorted(figures)}"
    return Plate(name, figures[name])


def plate_names(slug: str) -> list[str]:
    return sorted(_render(slug, "en"))


def close_all():
    plt.close("all")
    _render.cache_clear()
