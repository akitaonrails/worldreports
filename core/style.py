"""The shared visual identity for every plate in the atlas.

Editorial data-journalism look: warm paper background, a restrained palette
taken from the country's own flag, strong typographic hierarchy, consistent
event annotations and source footers. Everything the plate scripts need to
draw lives here, so the whole atlas can be re-styled from one file and a new
country inherits the look by declaring a palette rather than copying code.

The one thing that is *not* shared is colour: each `Infographic` is built
for a `Country` and draws from that country's palette, so a Brazilian plate
is green where a French one is blue without either script knowing about the
other.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.lines
import matplotlib.patches
import matplotlib.pyplot as plt
from matplotlib import font_manager

from core import i18n


# ---------------------------------------------------------------- fonts
def _available() -> set[str]:
    return {f.name for f in font_manager.fontManager.ttflist}


def _pick(candidates: list[str]) -> str | None:
    have = _available()
    for c in candidates:
        if c in have:
            return c
    return None


LATIN_TITLE = ["Liberation Sans", "Noto Sans", "DejaVu Sans"]
LATIN_BODY = ["Noto Sans", "Liberation Sans", "DejaVu Sans"]

# Korean labels render as tofu in the Latin faces, so a plate in `ko` needs a
# CJK family. This is keyed by language rather than by country: it is the
# text that needs the glyphs, not the subject. A Korean plate in English uses
# the Latin stack, and the Korean edition of any country's plate would use
# this one.
# A language whose script a Latin font cannot draw. Latin-only fonts render
# every Hangul glyph as a tofu box without raising anything, so these
# languages pick a face that covers the script, and the build refuses to
# render one for which no such face is installed.
#
# The pan-CJK Noto faces are one glyph set with different regional defaults
# for Han, so every one of them carries the whole Hangul block: "CJK JP" is
# a correct fallback for Korean, not an approximation. It is also the one
# matplotlib usually finds, because the family ships as an OpenType
# collection and font_manager indexes only its first face — fontconfig
# lists "Noto Sans CJK KR" on a machine where matplotlib sees only JP.
SCRIPT_FONTS = {
    "ko": ["Noto Sans CJK KR", "Noto Sans KR", "NanumGothic", "Malgun Gothic",
           "Noto Sans CJK JP", "Noto Sans CJK SC", "Noto Sans CJK HK",
           "Noto Sans CJK TC", "AppleGothic", "UnDotum"],
}

MONO_FONT = _pick(["Liberation Mono", "DejaVu Sans Mono"])


def title_font(lang: str | None = None) -> str | None:
    lang = lang or i18n.LANG
    if lang in SCRIPT_FONTS:
        return _pick(SCRIPT_FONTS[lang]) or _pick(LATIN_TITLE)
    return _pick(LATIN_TITLE)


def body_font(lang: str | None = None) -> str | None:
    lang = lang or i18n.LANG
    if lang in SCRIPT_FONTS:
        return _pick(SCRIPT_FONTS[lang]) or _pick(LATIN_BODY)
    return _pick(LATIN_BODY)


def has_script_font(lang: str) -> bool:
    """Whether this machine can render `lang` at all.

    CI installs the CJK fonts; a laptop may not. Rendering tofu silently
    would publish a plate nobody can read, so the chart runner checks this
    and says so instead.
    """
    return lang not in SCRIPT_FONTS or _pick(SCRIPT_FONTS[lang]) is not None


def apply_rc(country, lang: str | None = None) -> None:
    p = country.palette
    mpl.rcParams.update({
        "figure.facecolor": p.paper,
        "axes.facecolor": p.card,
        "savefig.facecolor": p.paper,
        "font.family": body_font(lang) or "DejaVu Sans",
        "font.size": 10.5,
        "axes.edgecolor": p.spine,
        "axes.linewidth": 0.8,
        "axes.labelcolor": p.muted,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.titlecolor": p.ink,
        "axes.titlepad": 10,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": p.grid,
        "grid.linewidth": 0.7,
        "xtick.color": p.muted,
        "ytick.color": p.muted,
        "xtick.labelsize": 9.5,
        "ytick.labelsize": 9.5,
        "legend.frameon": False,
        "legend.fontsize": 9.5,
        "axes.unicode_minus": False,
    })


# ---------------------------------------------------------------- figure
class Infographic:
    """A multi-panel editorial figure with a title block and source footer."""

    def __init__(self, country, title: str, subtitle: str, ncols: int = 2,
                 nrows: int = 2, figsize: tuple[float, float] = (16.0, 10.2),
                 source: str = "", right: float = 0.975):
        self.country = country
        self.p = country.palette
        apply_rc(country)
        self.title = title
        self.subtitle = subtitle
        self.source = source
        self.fig, self.axes = plt.subplots(
            nrows, ncols, figsize=figsize, dpi=110)
        # `right` is the only margin a plate ever needs to move. The
        # default leaves 2.5% of the width past the axes, which is enough
        # for a tick label and nothing else — so a panel in the right-hand
        # column carrying a second y-axis runs its ticks, and its axis
        # label, straight off the canvas. That is not a near miss: the
        # label is not drawn at all and the reader never learns what the
        # second axis measures. A plate with such a panel asks for the
        # room instead of hoping, and core.qa fails the build if it does
        # not. Every other margin is shared, so the plates of five
        # countries keep lining up with each other.
        self.fig.subplots_adjust(left=0.055, right=right, top=0.845,
                                 bottom=0.105, wspace=0.24, hspace=0.38)
        self.axes_flat = (self.axes.ravel()
                          if hasattr(self.axes, "ravel") else [self.axes])
        self._panel_idx = 0

    # ------------------------------------------------------------ panels
    def next_panel(self, label: str = ""):
        ax = self.axes_flat[self._panel_idx]
        self._panel_idx += 1
        if label:
            ax.set_title(label, loc="left", fontsize=12, fontweight="bold",
                         color=self.p.ink, fontfamily=title_font())
        return ax

    def style_axis(self, ax, xticks_years: bool = True,
                   n_xticks: int = 11) -> None:
        """Strip the chrome a panel does not need and set the year ticks.

        `n_xticks` is accepted and ignored: three of the five original
        projects declared it and none of them read it, and a caller still
        passes it.
        """
        years = self.country.years
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.spines["bottom"].set_color(self.p.spine)
        ax.tick_params(length=0)
        if xticks_years:
            ax.set_xticks([y for y in years
                           if y % self.country.tick_every == 0])
            ax.set_xlim(years[0] - 0.6, years[-1] + 0.6)
        ax.grid(axis="y", color=self.p.grid, linewidth=0.7)
        ax.set_axisbelow(True)

    # ------------------------------------------------- event annotations
    def add_event(self, ax, year: float, text: str, dy: float = 0.97,
                  color: str | None = None, rotation: int = 0,
                  fontsize: float = 7.8):
        ax.axvline(year, color=color or self.p.faint, lw=0.9, ls=(0, (4, 3)),
                   alpha=0.85, zorder=1)
        ax.text(year + 0.12, dy, text, transform=ax.get_xaxis_transform(),
                fontsize=fontsize, color=self.p.muted, rotation=rotation,
                ha="left", va="top", clip_on=False)

    def add_band(self, ax, start: float, end: float, label: str = "",
                 color: str | None = None, label_inside: bool = False):
        ax.axvspan(start, end, color=color or self.p.band, zorder=0)
        if label:
            if label_inside:
                ax.text((start + end) / 2, 0.06, label,
                        transform=ax.get_xaxis_transform(), ha="center",
                        fontsize=8, color=self.p.muted, style="italic")
            else:
                ax.text((start + end) / 2, 1.0, label,
                        transform=ax.get_xaxis_transform(), ha="center",
                        va="bottom", fontsize=8, color=self.p.muted,
                        style="italic", clip_on=False)

    def add_recessions(self, ax, label: bool = True,
                       inside: bool = False) -> None:
        """This country's downturn bands, on a time-series panel.

        They are the shared context: almost every series in this atlas
        turns at them. Labelled by default, because an unexplained grey
        stripe is worse than none; pass label=False on a panel where the
        caption would collide with the series.
        """
        for start, end, name in self.country.recessions:
            self.add_band(ax, start, end, name if label else "",
                          label_inside=inside)

    def headroom(self, ax, top: float = 0.20, bottom: float = 0.0) -> None:
        """Open space above (and below) the data.

        A value annotated above the tallest bar is drawn inside the axes
        while a band caption sits just outside the top of them, so without
        headroom the two land on the same row and overprint.
        """
        lo, hi = ax.get_ylim()
        span = hi - lo
        ax.set_ylim(lo - span * bottom, hi + span * top)

    def mark_partial(self, ax, year: int, tag: str | None = None):
        tag = tag or f"{year}: partial"
        ax.text(year, -0.16, tag, transform=ax.get_xaxis_transform(),
                ha="center", va="top", fontsize=8.5, color=self.p.faint,
                style="italic")

    # ---------------------------------------------------------- headline
    def _draw_header(self) -> None:
        self.fig.text(0.055, 0.965, self.title, fontsize=23, fontweight="bold",
                      color=self.p.ink, fontfamily=title_font(), ha="left",
                      va="top")
        self.fig.text(0.055, 0.905, self.subtitle, fontsize=12.5,
                      color=self.p.muted, ha="left", va="top")
        # The flag rule. A band the colour of the paper needs an outline:
        # an unstroked white rectangle on a #FBFAF7 page is a gap, and the
        # rule reads as two detached blocks rather than one tricolore.
        bands = list(self.p.flag_bands)
        for i, face in enumerate(bands):
            edge = self.p.spine if _is_paperish(face, self.p.paper) else "none"
            self.fig.patches.append(mpl.patches.Rectangle(
                (0.055 + i * 0.029, 0.986), 0.028, 0.007,
                transform=self.fig.transFigure, facecolor=face,
                edgecolor=edge, linewidth=0.4, zorder=5))

    def _draw_footer(self) -> None:
        self.fig.lines.append(mpl.lines.Line2D(
            [0.055, 0.975], [0.062, 0.062], transform=self.fig.transFigure,
            color=self.p.spine, lw=0.8))
        self.fig.text(0.055, 0.040, self.source, fontsize=8.6,
                      color=self.p.faint, ha="left", va="top")
        # The address is not translatable and the sentence beside it is, so
        # the sentence is looked up here and the line composed around it.
        # The result is then marked as already localised: left to the sweep
        # in save(), it would be looked up whole and reported as a missing
        # translation in every language, which is how a real gap elsewhere
        # would get lost in the noise.
        gen = (f"worldreports.io/{self.country.slug} · "
               f"{i18n.translate('generated from committed CSVs')}")
        artist = self.fig.text(0.975, 0.040, gen, fontsize=8.6,
                               color=self.p.faint, ha="right", va="top")
        i18n.mark_localized(artist)

    # ------------------------------------------------------------- save
    def save(self, path) -> Path:
        """Draw the frame, translate the finished figure, then write it.

        Translation happens here rather than at every call site, so a plate
        cannot be half-localised. English keeps the plain filename; other
        languages get a suffix, which leaves existing links working.
        """
        self._draw_header()
        self._draw_footer()
        i18n.localize(self.fig)
        path = Path(path)
        if i18n.LANG != "en":
            path = path.with_name(f"{path.stem}.{i18n.LANG}{path.suffix}")
        self.fig.savefig(path, dpi=170)
        self.fig.savefig(path.with_suffix(".svg"))
        plt.close(self.fig)
        return path


def _is_paperish(colour: str, paper: str) -> bool:
    """Whether a flag band would vanish into the page."""
    return colour.lower() in {paper.lower(), "#ffffff", "#fff", "white"}
