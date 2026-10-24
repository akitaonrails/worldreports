"""The drawing vocabulary every plate is written in.

These are the helpers that were copied, with small drifts, into all five of
the original repositories: read a CSV, pull a series out of it, draw a line
whose running year is dashed rather than solid, label the last point, hatch
a partial bar, say "data pending" in a panel whose source has not published
yet. They are the same in every country, so they live here once.

Everything that takes a country takes it explicitly. There is no module-level
"current country": a helper that read one would let a Brazilian plate pick up
France's `last_full_year` the moment both were rendered in one process.
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np


# ------------------------------------------------------------------ input
def read_table(path: Path) -> dict[str, list] | None:
    """Read a CSV into {column: list[float|str]}, year as int, text kept.

    Blanks become NaN rather than 0 or None, because every plate tests for a
    hole with `v == v` and because a year the source has not published is a
    gap in the line, not a collapse to zero.
    """
    path = Path(path)
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        # Leading '#' lines carry provenance a YAML note cannot hold — a
        # series break, a scope warning, "this is an industry survey, not an
        # official statistic" — so the caveat travels with the data. Read
        # naively, the first of them becomes the header and every column
        # goes missing. `comments()` reads them back out.
        rows = list(csv.DictReader(
            ln for ln in f if not ln.lstrip().startswith("#")))
    if not rows:
        return None
    cols: dict[str, list] = {}
    for key in rows[0]:
        vals = []
        for r in rows:
            v = (r.get(key) or "").strip()
            if not v:
                vals.append(np.nan)
            elif key == "year":
                vals.append(int(float(v)))
            else:
                try:
                    vals.append(float(v))
                except ValueError:
                    vals.append(v)
        cols[key] = vals
    return cols


def comments(path: Path) -> list[str]:
    """The '#' provenance lines at the top of a CSV, in order.

    Read by the SOURCES.md generator and asserted on by the tests, so a
    caveat written next to the numbers cannot be dropped silently when the
    file is regenerated.
    """
    path = Path(path)
    if not path.exists():
        return []
    out = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if not line.lstrip().startswith("#"):
                break
            out.append(line.lstrip().lstrip("#").strip())
    return out


def series(t: dict, col: str) -> tuple[list[int], list[float]]:
    """(years, values) for one column, with the blanks dropped.

    Blanks are dropped rather than zero-filled: a year the source has not
    published is a hole in the line, not a collapse to zero.
    """
    yrs = t.get("year", [])
    vals = t.get(col, [np.nan] * len(yrs))
    keep = [(y, v) for y, v in zip(yrs, vals) if v == v]
    return [k[0] for k in keep], [k[1] for k in keep]


def nan(vals) -> np.ndarray:
    """A float array where None and missing entries are NaN."""
    return np.array([np.nan if v is None else float(v) for v in vals],
                    dtype=float)


# ------------------------------------------------------------------ lines
def line(ax, years, vals, color, label="", lw=2.4, marker="o", ms=4.2,
         dashed_partial=True, zorder=3, split_year=None, ls="-",
         last_full_year=None):
    """Solid up to the last full year, dashed after it.

    The tail is thinner, lighter and dashed because those years are partial
    or projected. Pass `split_year` to move the break (a series whose own
    last complete year is earlier than the country's).
    """
    split = split_year if split_year is not None else last_full_year
    if split is None:
        raise ValueError(
            "line() needs last_full_year=country.last_full_year or an "
            "explicit split_year; without one the partial tail is drawn as "
            "though it were a complete year")
    full = [(y, v) for y, v in zip(years, vals) if v == v]
    seg_full = [(y, v) for y, v in full if y <= split]
    seg_part = [(y, v) for y, v in full if y >= split]
    kw = dict(color=color, lw=lw, marker=marker, ms=ms, zorder=zorder,
              solid_capstyle="round", label=label, ls=ls)
    if seg_full:
        fy, fv = zip(*seg_full)
        ax.plot(fy, fv, **kw)
    if seg_part:
        py, pv = zip(*seg_part)
        kw2 = dict(kw)
        if seg_full:
            # The full-year segment already carries the legend entry; without
            # this the dashed tail adds a second one for the same series.
            kw2["label"] = "_nolegend_"
        kw2["lw"] = lw * (0.55 if dashed_partial else 1)
        kw2["alpha"] = 0.65
        kw2["ls"] = "--" if dashed_partial else ls
        ax.plot(py, pv, **kw2)


def bars(ax, years, vals, color_fn, width=0.72, hatch_partial=True, edge=None,
         last_full_year=None):
    """Bars, with anything past the last full year hatched and faded."""
    if last_full_year is None:
        raise ValueError("bars() needs last_full_year=country.last_full_year")
    for y, v in zip(years, vals):
        if v != v:
            continue
        partial = y > last_full_year
        ax.bar(y, v, width=width,
               color=color_fn(v) if callable(color_fn) else color_fn,
               alpha=0.62 if partial and hatch_partial else 1.0,
               hatch="//" if partial and hatch_partial else None,
               edgecolor=edge or "white", linewidth=0.6, zorder=3)


def endlabel(ax, years, vals, color, fmt=lambda v: f"{v:,.1f}", dy=8,
             fontsize=9.5, ha="right"):
    """Print the last value of a series at its end point."""
    pts = [(y, v) for y, v in zip(years, vals) if v == v]
    if not pts:
        return
    last = pts[-1]
    ax.annotate(fmt(last[1]), (last[0], last[1]), textcoords="offset points",
                xytext=(-2, dy), fontsize=fontsize, fontweight="bold",
                color=color, ha=ha, zorder=6)


def annotate_value(ax, x, y, text, color, offset=(0, 10), fontsize=9,
                   weight="bold", ha="center"):
    ax.annotate(text, (x, y), textcoords="offset points", xytext=offset,
                fontsize=fontsize, fontweight=weight, color=color, ha=ha,
                va="bottom", zorder=6)


# --------------------------------------------------------- partial years
def full_years(years, vals, last_full_year):
    """Only the years that are complete.

    An annual flow for a year still running is not comparable with the ones
    before it; plotted on the same line it draws a collapse that never
    happened. Levels and point-in-time readings are exempt — this is for
    totals and averages only.
    """
    keep = [(y, v) for y, v in zip(years, vals) if y <= last_full_year]
    return [y for y, _ in keep], [v for _, v in keep]


def partial_row(table: dict, last_full_year: int) -> dict | None:
    """The first incomplete year's row, so a panel can state it in words.

    The year stays in the row: a caption that says which months it covers
    needs to name the year too, and hardcoding it at the call site is how a
    caption outlives the year it was written for.
    """
    for i, y in enumerate(table.get("year", [])):
        if y > last_full_year:
            row = {k: v[i] for k, v in table.items()}
            data = [v for k, v in row.items() if k != "year"]
            return row if any(v == v for v in data) else None
    return None


# ------------------------------------------------------------------ chrome
def source(*parts: str) -> str:
    """The footer line. Translated as a whole by core.i18n."""
    return "Sources: " + " · ".join(p for p in parts if p)


def pending(ax, palette) -> None:
    """Fill a panel whose source has not published yet.

    Drawn rather than left blank so a missing series is obvious in review
    instead of looking like an empty axis someone forgot to delete.
    """
    ax.text(0.5, 0.5, "data pending — run fetchers / add CSV",
            transform=ax.transAxes, ha="center", va="center",
            fontsize=11, color=palette.faint, style="italic")
    ax.grid(False)
    # A spine slot with nothing in it keeps its place on the grid. The
    # shared scale is applied later by Infographic.apply_spine, because an
    # empty overlay must still register with a peer that has data.
    ax.spine_pending = True


# ------------------------------------------------------------- formatting
# Money formatting is deliberately NOT here. The five countries round and
# threshold differently -- France never writes trillions, Argentina switches
# at a million pesos, the USA tests abs(v) -- and a shared "compact dollars"
# helper would silently reprint someone's numbers. Each country keeps its own
# in its plates.py or money.py.
