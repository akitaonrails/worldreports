"""What a plate drew, read back off its axes, so the viewer can answer
"what was it that year?" when a reader points at a panel.

A plate is a picture. The numbers are in it only as pixels, so the site
cannot say what a bar or a line stood for at a given year unless the render
writes it down. This reads them from the finished figure (after the spine
has fixed the limits and the translation has run), the same artists
`spine.data_extent` already walks, so a value shown on hover is the value
that was drawn and cannot drift from it.

One file per plate and language, beside the picture it describes:
`01_economy.pt.hover.json`. For every spine panel it holds where the axes
sit on the picture (fractions of its width and height, top left origin), the
limits, and the series, each as (x, y) pairs. Nothing here names a country.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from matplotlib.collections import PolyCollection
from matplotlib.patches import Patch
from matplotlib.colors import to_hex

from core import i18n

SUFFIX = ".hover.json"
CALENDAR = 1000    # a time axis starts at a year, not at 0 or -1
SIG = 5            # significant digits kept: the picture cannot show more


def path_for(picture: Path) -> Path:
    """The file that describes a saved plate, whichever format `picture` is."""
    return picture.with_name(picture.stem + SUFFIX)


def _round(v: float) -> float:
    v = float(v)
    if v == 0 or not math.isfinite(v):
        return v
    return round(v, SIG - 1 - int(math.floor(math.log10(abs(v)))))


def _names(ax) -> dict[str, str]:
    """Each series label as the legend printed it, in the plate's language.

    Localisation rewrites the legend's text, not the artists' labels, and a
    legend entry's handle keeps the label it was made from.
    """
    legend = ax.get_legend()
    if legend is None:
        return {}
    return {h.get_label(): t.get_text()
            for h, t in zip(legend.legend_handles, legend.get_texts())}


def _name(artist, names) -> str:
    label = artist.get_label() or ""
    if label.startswith("_"):
        return ""
    # a name the plate did not print is told in its language if the catalog
    # knows it, and left blank rather than half in English if it does not
    return names.get(label) or i18n.known(label) or ""


def _hex(colour) -> str:
    try:
        return to_hex(colour)
    except (TypeError, ValueError):
        return ""


def _pairs(x, y) -> list[list[float]]:
    out = []
    for a, b in zip(np.asarray(x, dtype=float), np.asarray(y, dtype=float)):
        if math.isfinite(a) and math.isfinite(b):
            out.append([_round(a), _round(b)])
    return out


def _merge(into: list[list[float]], more: list[list[float]]) -> None:
    """Add points, keeping one per x: a partial-year segment is drawn over
    the line it continues, and both carry the year they share."""
    have = {p[0] for p in into}
    into.extend(p for p in more if p[0] not in have)
    into.sort(key=lambda p: p[0])


def _lines(ax, names) -> list[dict]:
    """Lines, grouped by what they are called and coloured, so the dashed
    stretch of a line joins the line it continues."""
    groups: dict[tuple, dict] = {}
    for ln in ax.get_lines():
        if ln.get_transform() is not ax.transData:
            continue
        pts = _pairs(ln.get_xdata(), ln.get_ydata())
        if len(pts) < 2:
            continue
        key = (_name(ln, names), _hex(ln.get_color()))
        g = groups.setdefault(key, {"kind": "line", "name": key[0],
                                    "color": key[1], "pts": []})
        _merge(g["pts"], pts)
    # an unnamed stretch continues the named line it is drawn like (a series
    # broken into runs is labelled once) or the one that ends where it starts
    # (the dashed part-year)
    named = [g for g in groups.values() if g["name"]]
    for g in [g for g in groups.values() if not g["name"]]:
        head = g["pts"][0][0]
        home = next((n for n in named if n["color"] == g["color"]), None) \
            or next((n for n in named
                     if any(p[0] == head for p in n["pts"])), None)
        if home:
            _merge(home["pts"], g["pts"])
            del groups[("", g["color"])]
    # a short unnamed line that continues nothing is a rule or a connector,
    # not a series
    return [g for g in groups.values() if g["name"] or len(g["pts"]) > 2]


def _patch_entry(ax) -> tuple[str, str]:
    """The name and colour of the legend's one swatch for bars, if it has one.

    A bar chart is not a labelled artist: its legend line is a separate
    swatch. The swatches of filled regions are not it, they name the
    region that was drawn with the same label.
    """
    legend = ax.get_legend()
    if legend is None:
        return "", ""
    regions = {c.get_label() for c in ax.collections}
    for h, t in zip(legend.legend_handles, legend.get_texts()):
        if isinstance(h, Patch) and h.get_label() not in regions:
            return t.get_text(), _hex(h.get_facecolor())
    return "", ""


def _bars(ax) -> list[dict]:
    """Vertical bars, one point per bar at its centre: the signed height,
    added up where bars are stacked on one another."""
    bars = [p for p in ax.patches
            if p.get_data_transform() is ax.transData
            and hasattr(p, "get_height") and p.get_width() > 0]
    # bars laid on their side (all one thickness, lengths varying) have no
    # year to point at
    if (len(bars) > 1
            and len({round(float(p.get_height()), 6) for p in bars}) == 1
            and len({round(float(p.get_width()), 6) for p in bars}) > 1):
        return []
    heights: dict[float, float] = {}
    for p in bars:
        h = float(p.get_height())
        if not math.isfinite(h):
            continue
        x = _round(float(p.get_x()) + float(p.get_width()) / 2)
        heights[x] = heights.get(x, 0.0) + h
    if not heights:
        return []
    name, colour = _patch_entry(ax)
    return [{"kind": "bar", "name": name, "color": colour,
             "pts": [[x, _round(v)] for x, v in sorted(heights.items())]}]


def _edges(poly) -> tuple[list[float], list[float], list[float]]:
    """x, lower and upper edge of a filled region at each whole year.

    The outline is cut by a vertical line through the year: the lowest and
    highest crossing are the edges. A stepped region has two corners at each
    step, which a read of its corners alone would mix up.
    """
    v = np.asarray(poly.get_paths()[0].vertices, dtype=float)
    v = v[np.isfinite(v).all(axis=1)]
    if len(v) < 2:
        return [], [], []
    sides = list(zip(v[:-1], v[1:]))
    xs, lo, hi = [], [], []
    for year in range(math.ceil(v[:, 0].min() - 1e-9),
                      math.floor(v[:, 0].max() + 1e-9) + 1):
        ys = [y0 + (y1 - y0) * (year - x0) / (x1 - x0)
              for (x0, y0), (x1, y1) in sides
              if x0 != x1 and min(x0, x1) - 1e-9 <= year <= max(x0, x1) + 1e-9]
        if ys:
            xs.append(float(year))
            lo.append(min(ys))
            hi.append(max(ys))
    return xs, lo, hi


def _fills(ax, names) -> list[dict]:
    """Filled regions: a layer of a stack reads as its thickness, a band
    between two lines as the pair of edges."""
    polys = [c for c in ax.collections
             if c.get_transform() is ax.transData
             and isinstance(c, PolyCollection) and c.get_paths()]
    edges = [(c, *_edges(c)) for c in polys]
    out = []
    for c, xs, lo, hi in edges:
        if len(xs) < 2:
            continue
        others = [oh for o, ox, _, oh in edges if o is not c and ox == xs]
        stacked = (all(abs(v) < 1e-9 for v in lo)
                   or any(np.allclose(lo, h) for h in others))
        if stacked:
            pts = [[_round(x), _round(h - l)] for x, l, h in zip(xs, lo, hi)]
        else:
            pts = [[_round(x), _round(l), _round(h)]
                   for x, l, h in zip(xs, lo, hi)]
        face = c.get_facecolor()
        # a band nobody named has nothing to say beside its lines
        if not stacked and not _name(c, names):
            continue
        out.append({"kind": "layer" if stacked else "band",
                    "name": _name(c, names),
                    "color": _hex(face[0]) if len(face) else "", "pts": pts})
    return out


def _grouped(ax, names) -> tuple[list[dict], list[list]] | None:
    """Bars side by side in groups, one labelled container per series: the
    series, and the groups as (position, tick label).

    The groups, not the bars, are what a reader points at: a year, with every
    series' bar beside it. Returns None for anything that is not that.
    """
    boxes = [c for c in ax.containers
             if getattr(c, "patches", None) and _name(c, names)]
    if len(boxes) < 2:
        return None
    series = []
    for c in boxes:
        series.append({
            "kind": "bar", "name": _name(c, names),
            "color": _hex(c.patches[0].get_facecolor()),
            "pts": [[_round(p.get_x() + p.get_width() / 2),
                     _round(p.get_height())] for p in c.patches],
        })
    ax.figure.canvas.draw()          # tick labels are made on a draw
    groups = [[_round(float(t.get_position()[0])), t.get_text()]
              for t in ax.get_xticklabels() if t.get_text()]
    return (series, groups) if groups else None


def _dots(ax, names) -> list[dict]:
    """Scatter points: markers placed at data coordinates."""
    out = []
    for c in ax.collections:
        if (type(c).__name__ != "PathCollection"
                or c.get_offset_transform() is not ax.transData):
            continue
        off = np.asarray(c.get_offsets(), dtype=float)
        if off.size:
            out.append({"kind": "dots", "name": _name(c, names), "color": "",
                        "pts": _pairs(off[:, 0], off[:, 1])})
    return out


def panel(ax) -> dict | None:
    """One panel as the viewer needs it, or None if it drew no series."""
    names = _names(ax)
    groups = None
    if ax.get_xlim()[0] < CALENDAR:
        # not a calendar: only bars in labelled groups can be pointed at
        found = _grouped(ax, names)
        if found is None:
            return None
        series, groups = found
    else:
        series = [s for s in (_fills(ax, names) + _lines(ax, names)
                              + _bars(ax) + _dots(ax, names)) if s["pts"]]
    if not series:
        return None
    pos = ax.get_position()
    out = {
        "box": [_round(pos.x0), _round(1 - pos.y1),
                _round(pos.width), _round(pos.height)],
        "xlim": [_round(v) for v in ax.get_xlim()],
        "ylim": [_round(v) for v in ax.get_ylim()],
        "log": ax.get_yscale() == "log",
        "unit": ax.get_ylabel(),
        "title": ax.get_title(loc="left"),
        "series": series,
    }
    if groups:
        out["groups"] = groups
    return out


def read(axes) -> dict:
    """Every claimed, visible spine panel that drew something, by slot key."""
    out = {}
    for ax in axes:
        slot = getattr(ax, "spine_slot", None)
        if (slot is None or not ax.get_visible()
                or getattr(ax, "spine_pending", False)):
            continue
        found = panel(ax)
        if found:
            out[slot.key] = found
    return out


def write(picture: Path, axes) -> Path | None:
    """Write the description beside `picture`; nothing if no panel has any."""
    found = read(axes)
    if not found:
        return None
    path = path_for(picture)
    path.write_text(json.dumps(found, ensure_ascii=False,
                               separators=(",", ":")), encoding="utf-8")
    return path
