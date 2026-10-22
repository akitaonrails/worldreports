"""Programmatic layout check for a rendered plate.

Rendering a figure proves nothing about whether it can be read: matplotlib
will happily stack an annotation on top of a legend, run a caption off the
canvas, or let a note sit over the bars it describes. Across five
countries that is fifty-two plates in thirteen language combinations —
far past what anyone checks by eye, and the language that breaks is
rarely the one that was looked at, because the Spanish, Portuguese and
French strings are longer than the English ones they replace.

This walks a rendered figure and reports four faults:

  OVERLAP   two pieces of text whose boxes intersect
  OUTSIDE   text that extends past the edge of the canvas
  CLIPPED   text that leaves the axes it belongs to while clipping is on,
            so part of it will simply not be drawn
  ONDATA    text sitting on top of a bar or a line — legible in the sense
            that both are drawn, unreadable in the sense that matters

Tick labels are excluded from OVERLAP against each other — matplotlib
spaces those itself and a near-touch there is not a defect — but they are
checked against everything else, because a value label landing on the axis
is one of the commonest ways a plate goes wrong.

Grown in one of the five original projects, where a Spanish caption twice
grew two lines longer than its English original and landed on the series
it described. Shared here, so the other four get the check for free and a
country added later does too. See tests/test_layout.py.
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")

# Boxes closer than this many points are treated as touching, not as a
# collision: matplotlib's own padding is tighter than the eye's.
TOLERANCE = 1.0
# A value label resting on the top edge of its own bar is not a collision.
ONDATA_TOLERANCE = 4.0
# A chart script marks a label that is *meant* to sit on the data — a count
# written inside its own bar — with this gid. Nothing else is exempt.
ALLOWED = "qa-on-data"


def boxes(fig):
    """Every visible string in the figure, tagged by what kind it is.

      tick     axis tick labels — matplotlib lays these out itself
      chrome   panel titles and axis labels — these legitimately sit
               outside the axes box, so the clipping rule must not apply
      content  everything a chart script wrote: annotations, notes,
               legends, value labels
    """
    renderer = fig.canvas.get_renderer()
    out = []
    for ax in fig.get_axes():
        chrome = {id(a) for a in (ax.title, ax.xaxis.label, ax.yaxis.label)}
        chrome.update(id(a) for a in ax._children
                      if isinstance(a, matplotlib.text.Text)
                      and a in (getattr(ax, "_left_title", None),
                                getattr(ax, "_right_title", None)))
        for a in (getattr(ax, "_left_title", None),
                  getattr(ax, "_right_title", None)):
            if a is not None:
                chrome.add(id(a))
        ticks = set()
        for axis in (ax.xaxis, ax.yaxis):
            ticks.update(id(a) for a in axis.get_ticklabels())
            ticks.add(id(axis.offsetText))
        for text in ax.findobj(matplotlib.text.Text):
            if not text.get_text().strip() or not text.get_visible():
                continue
            try:
                # Text.get_window_extent, not the subclass override:
                # Annotation's own version unions the text box with its
                # leader line, so a callout joined to the point it explains
                # would always look like it was sitting on the data.
                bbox = matplotlib.text.Text.get_window_extent(
                    text, renderer=renderer)
                # A note drawn in a rounded box occupies the box, not the
                # glyphs: its padding hid a peak label that the text
                # extents alone said was clear.
                patch = text.get_bbox_patch()
                if patch is not None:
                    bbox = patch.get_window_extent(renderer=renderer)
            except Exception:  # noqa: BLE001
                continue
            kind = ("tick" if id(text) in ticks
                    else "chrome" if id(text) in chrome else "content")
            out.append((text, bbox, ax, kind))
    for text in fig.texts:
        if text.get_text().strip() and text.get_visible():
            out.append((text, matplotlib.text.Text.get_window_extent(
            text, renderer=renderer), None, "content"))
    return out


def drawn(ax):
    """The bars and line vertices of one panel, in display coordinates.

    A bar is its rectangle; a line is its points. A line's bounding box
    would condemn every caption on a rising series, so the test is against
    the vertices themselves.
    """
    rectangles, points = [], []
    for patch in ax.patches:
        # zorder 0 is the background: the INDEC band, the cepo shading.
        # Those are meant to be written on.
        if (isinstance(patch, matplotlib.patches.Rectangle)
                and patch.get_zorder() >= 1):
            box = patch.get_window_extent()
            if box.width > 0.5 and box.height > 0.5:
                rectangles.append(box)
    for line2d in ax.lines:
        data = line2d.get_xydata()
        # Two points is an axvline or an axhline: a reference mark, not a
        # series. Annotations are meant to touch those.
        if len(data) > 2:
            points.extend(ax.transData.transform(data))
    return rectangles, points


def intersects(a, b, tolerance: float = TOLERANCE) -> bool:
    return not (a.x1 - tolerance <= b.x0 or b.x1 - tolerance <= a.x0
                or a.y1 - tolerance <= b.y0 or b.y1 - tolerance <= a.y0)


def short(text) -> str:
    body = " ".join(text.get_text().split())
    return body if len(body) <= 46 else body[:43] + "…"


def inspect(fig) -> list[str]:
    fig.canvas.draw()
    items = boxes(fig)
    canvas = fig.bbox
    faults: list[str] = []

    for text, bbox, ax, kind in items:
        # Tick labels are skipped here: matplotlib keeps generating them
        # for locations outside the view limits, and a label for a tick
        # that is never drawn is not a layout fault.
        if kind == "tick":
            continue
        if (bbox.x0 < canvas.x0 - TOLERANCE or bbox.x1 > canvas.x1 + TOLERANCE
                or bbox.y0 < canvas.y0 - TOLERANCE
                or bbox.y1 > canvas.y1 + TOLERANCE):
            faults.append(f"OUTSIDE  {short(text)!r}")
        if ax is not None and kind == "content" and text.get_clip_on():
            frame = ax.bbox
            if (bbox.x0 < frame.x0 - TOLERANCE or bbox.x1 > frame.x1 + TOLERANCE
                    or bbox.y0 < frame.y0 - TOLERANCE
                    or bbox.y1 > frame.y1 + TOLERANCE):
                faults.append(f"CLIPPED  {short(text)!r}")

    for i, (ta, ba, axa, kind_a) in enumerate(items):
        for tb, bb, axb, kind_b in items[i + 1:]:
            # matplotlib lays out ticks and panel chrome itself; a
            # near-touch between two of those is not a defect.
            if kind_a != "content" and kind_b != "content":
                continue
            if axa is not None and axb is not None and axa is not axb:
                continue
            if intersects(ba, bb):
                faults.append(f"OVERLAP  {short(ta)!r}  ×  {short(tb)!r}")

    for ax in fig.get_axes():
        rectangles, points = drawn(ax)
        for text, bbox, owner, kind in items:
            if kind != "content" or owner is not ax:
                continue
            if text.get_gid() == ALLOWED:
                continue
            if any(intersects(bbox, r, ONDATA_TOLERANCE)
                   for r in rectangles):
                faults.append(f"ONDATA   {short(text)!r} over a bar")
                continue
            pad = ONDATA_TOLERANCE
            if any(bbox.x0 - pad <= x <= bbox.x1 + pad
                   and bbox.y0 - pad <= y <= bbox.y1 + pad
                   for x, y in points):
                faults.append(f"ONDATA   {short(text)!r} over a line")
    return faults
