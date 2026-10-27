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
import re

import matplotlib as mpl
import matplotlib.lines
import matplotlib.patches
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib import ticker as mticker

from core import hover, i18n, spine


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
    # DejaVu Sans covers Hebrew and the Latin/numeric fragments that appear
    # beside it in data labels. Noto Sans Hebrew is Hebrew-only, so using it
    # alone turns years, units and source acronyms into missing glyphs.
    "he": ["DejaVu Sans", "Noto Sans Hebrew", "Arial Hebrew", "Arial"],
    "ko": ["Noto Sans CJK KR", "Noto Sans KR", "NanumGothic", "Malgun Gothic",
           "Noto Sans CJK JP", "Noto Sans CJK SC", "Noto Sans CJK HK",
           "Noto Sans CJK TC", "AppleGothic", "UnDotum"],
    "ja": ["Noto Sans CJK JP", "Noto Sans JP", "Yu Gothic", "Meiryo"],
    "zh-Hans": ["Noto Sans CJK SC", "Noto Sans SC", "Noto Sans CJK JP"],
    "zh-Hant": ["Noto Sans CJK TC", "Noto Sans TC", "Noto Sans CJK JP"],
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
                 source: str = "", right: float = 0.955,
                 topic: str | None = None):
        self.country = country
        self.p = country.palette
        # A plate that declares its topic is drawn on the spine: the one
        # frame, the one time axis, panels claimed with slot(). See
        # core/spine.py and PLATE_SPINE.md. None is a plate not migrated
        # yet, which keeps drawing exactly as it always has.
        self.topic = topic
        if topic is not None:
            spine.slots(topic)
            frame = {"nrows": nrows, "ncols": ncols,
                     "figsize": tuple(float(v) for v in figsize),
                     "right": right}
            if frame != spine.FRAME:
                raise spine.SpineError(
                    f"{country.slug}/{topic}: a spine plate is drawn on "
                    f"{spine.FRAME}, not {frame}")
            if country.tick_every != spine.TICK_EVERY:
                raise spine.SpineError(
                    f"{country.slug}/{topic}: a spine plate labels every "
                    f"{spine.TICK_EVERY}nd year; country.yaml has "
                    f"tick_every: {country.tick_every}")
        self._next_slot = 0
        #: Where save() wrote the plate (its English path), once it has.
        self.saved_as: Path | None = None
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
        # countries keep lining up with each other. The default is the
        # spine's 0.955 (PLATE_SPINE.md rule 1), which has room for a
        # right-hand axis label, so plates register at the same width.
        self.fig.subplots_adjust(left=0.055, right=right, top=0.845,
                                 bottom=0.105, wspace=0.24, hspace=0.38)
        self.axes_flat = (self.axes.ravel()
                          if hasattr(self.axes, "ravel") else [self.axes])
        self._panel_idx = 0

    # ------------------------------------------------------------ panels
    def next_panel(self, label: str = ""):
        if self.topic is not None:
            raise spine.SpineError(
                f"{self.country.slug}/{self.topic}: a spine plate claims its "
                f"panels with slot(key, title), not next_panel()")
        ax = self.axes_flat[self._panel_idx]
        self._panel_idx += 1
        if label:
            self._title(ax, label)
        return ax

    def _title(self, ax, label: str) -> None:
        ax.set_title(label, loc="left", fontsize=12, fontweight="bold",
                     color=self.p.ink, fontfamily=title_font())

    def slot(self, key: str, label: str = "", unit: bool = True):
        """The panel for one spine slot, titled and tagged.

            ax = ig.slot("economy.growth", "Real GDP growth (% per year)")

        Slots are claimed in spine order. Claiming one before a canonical
        slot that comes ahead of it fails here rather than publishing a
        plate whose panels sit in the wrong places; a lens slot (always
        last in its topic) may be left unclaimed. The panel is the slot's
        own position on the grid, so slot 3 is bottom-left whatever came
        before it.

        The axes carries its key as its gid and as `ax.spine_slot`. A
        signed slot gets its zero line now and a log slot its log scale,
        so the plate draws onto the right axis; the shared range is applied
        in save(), after the drawing, so overflow is caught. `unit=False`
        leaves the shared unit off the
        y-axis label, for a panel that states it some other way.
        """
        where = f"{self.country.slug}/{self.topic}"
        if self.topic is None:
            raise spine.SpineError(
                f"{self.country.slug}: slot({key!r}) on a plate with no "
                f"topic; pass topic= to ctx.fig or the PLATES entry")
        s = spine.SLOTS.get(key)
        if s is None or s.topic != self.topic:
            raise spine.SpineError(
                f"{where}: {key!r} is not one of this topic's slots "
                f"{[x.key for x in spine.slots(self.topic)]}")
        order = spine.slots(self.topic)
        i = order.index(s)
        if i < self._next_slot:
            raise spine.SpineError(
                f"{where}: {key!r} claimed after "
                f"{order[self._next_slot - 1].key!r}; slots go in spine "
                f"order, once each")
        skipped = [x.key for x in order[self._next_slot:i] if x.canonical]
        if skipped:
            raise spine.SpineError(
                f"{where}: {key!r} claimed before {skipped}; slots go in "
                f"spine order — draw those first, or ctx.pending them")
        self._next_slot = self._panel_idx = i + 1
        ax = self.axes_flat[i]
        ax.set_gid(key)
        ax.spine_slot = s
        ax.spine_unit = s.unit
        if label:
            self._title(ax, label)
        if unit and s.unit:
            ax.set_ylabel(s.unit, fontsize=8.6, color=self.p.muted)
        if s.zero:
            ax.axhline(0, color=self.p.muted, lw=0.9, zorder=2)
        if s.scale == spine.LOG:
            ax.set_yscale("log")
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

    # ------------------------------------------------------------ spine
    def apply_spine(self) -> None:
        """Put every canonical panel on its reference scale.

        Run after the plate has drawn, so the limits can see every value.
        Every canonical panel gets exactly the atlas-wide range, including
        a visibly pending one. Data that leave it fail the render so a
        maintainer widens the one shared range and regenerates every peer;
        one country's SVG must never acquire a different pixel transform.
        Lens slots remain country-specific. Does nothing off the spine.
        """
        if self.topic is None:
            return
        where = f"{self.country.slug}/{self.topic}"
        for i, s in enumerate(spine.slots(self.topic)):
            ax = self.axes_flat[i]
            if getattr(ax, "spine_slot", None) is None:
                if s.canonical:
                    raise spine.SpineError(
                        f"{where}: slot {i + 1} ({s.key}) was never "
                        f"claimed; claim it and ctx.pending it if the "
                        f"data do not exist")
                if spine.data_extent(ax) is not None:
                    raise spine.SpineError(
                        f"{where}: slot {i + 1} has data but was never "
                        f"claimed as {s.key}")
                ax.set_visible(False)
                continue
            if not s.canonical:
                continue
            (lo, hi), grew = spine.fit(s, spine.data_extent(ax))
            if s.scale == spine.LOG:
                ax.set_yscale("log")
                ax.yaxis.set_major_locator(
                    mticker.FixedLocator(spine.log_ticks(s, lo, hi)))
                ax.yaxis.set_major_formatter(
                    mticker.FuncFormatter(spine.tick_label))
                ax.yaxis.set_minor_locator(mticker.NullLocator())
            ax.set_ylim(lo, hi)
            ax.spine_extended = grew

    # ------------------------------------------------------------- save
    def compose(self) -> None:
        """Everything save() does to the figure before writing it.

        Separate so the tests can inspect exactly what would be written:
        the spine scales, the header and footer, then the translation.
        """
        self.apply_spine()
        self._draw_header()
        self._draw_footer()
        i18n.localize(self.fig)

    def save(self, path) -> Path:
        """Draw the frame, translate the finished figure, then write it.

        Translation happens here rather than at every call site, so a plate
        cannot be half-localised. English keeps the plain filename; other
        languages get a suffix, which leaves existing links working.
        """
        self.compose()
        path = Path(path)
        self.saved_as = path
        if i18n.LANG != "en":
            path = path.with_name(f"{path.stem}.{i18n.LANG}{path.suffix}")
        self.fig.savefig(path, dpi=170)
        svg = path.with_suffix(".svg")
        self.fig.savefig(svg)
        # Matplotlib emits trailing spaces in multi-line SVG path data.
        # Git treats them as whitespace errors; normalise the generated
        # artifact centrally so every render is diff-check clean.
        raw = svg.read_bytes()
        clean = re.sub(rb"[ \t]+(?=\r?$)", b"", raw, flags=re.MULTILINE)
        if clean != raw:
            svg.write_bytes(clean)
        hover.write(path, self.axes_flat)
        plt.close(self.fig)
        return path


def _is_paperish(colour: str, paper: str) -> bool:
    """Whether a flag band would vanish into the page."""
    return colour.lower() in {paper.lower(), "#ffffff", "#fff", "white"}
