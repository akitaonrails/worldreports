"""The political and economic timeline the plates annotate.

Kept apart from the charts so that every plate dates the same event the same
way, and so that a date can be corrected in one place.

Years are fractional — 2017.36 is mid-May 2017 — because a presidency that
begins in February and one that begins in May land in different halves of a
chart, and rounding both to the year would put Moon Jae-in's inauguration
before Park Geun-hye's removal.

Only events with a visible trace in the committed data earn a line. A plate
that annotates everything annotates nothing.
"""
from __future__ import annotations

# ------------------------------------------------------------ presidencies
# (start, end, surname, party lean) — `end` is the day the term actually
# ended, which twice was not the day it was meant to. Two of the six
# presidencies in this window were cut short by impeachment, and the gaps are
# the acting presidencies, drawn as a seam rather than given to either side.
PRESIDENTS: list[tuple[float, float, str, str]] = [
    (2003.15, 2008.15, "Roh", "liberal"),
    (2008.15, 2013.15, "Lee M-b", "conservative"),
    (2013.15, 2017.19, "Park", "conservative"),      # removed 10 Mar 2017
    (2017.36, 2022.36, "Moon", "liberal"),            # inaugurated 10 May 2017
    (2022.36, 2025.26, "Yoon", "conservative"),       # removed 4 Apr 2025
    (2025.42, 2026.99, "Lee J-m", "liberal"),         # inaugurated 4 Jun 2025
]

# ------------------------------------------------------------------ shocks
# Dated to when the data moves, not to when the news broke.
SHOCKS: dict[str, tuple[float, str]] = {
    "crisis": (2008.75, "global crisis"),
    "euro": (2011.6, "euro debt crisis"),
    "mers": (2015.45, "MERS outbreak"),
    "impeachment": (2017.19, "Park removed"),
    "thaad": (2017.2, "THAAD: China retaliates"),
    "japan": (2019.55, "Japan export curbs"),
    "covid": (2020.15, "COVID-19"),
    "energy": (2022.5, "energy import bill"),
    "martial_law": (2024.92, "martial law, 3 Dec"),
    "ai": (2025.5, "AI chip supercycle"),
}

# Shaded spans rather than lines: a shock with a duration.
BANDS: dict[str, tuple[float, float, str]] = {
    "crisis": (2008.75, 2009.4, "global crisis"),
    "covid": (2020.0, 2020.9, "COVID-19"),
    "pandemic": (2020.0, 2023.4, "pandemic"),
}


def band(name: str) -> tuple[float, float, str]:
    return BANDS[name]


def shock(name: str) -> tuple[float, str]:
    return SHOCKS[name]


def term_boundaries(first: int, last: int) -> list[tuple[float, str]]:
    """(x, surname) for every presidency that starts inside the window.

    Used by the plates that draw a political timeline strip. Roh's term began
    before the atlas does, so his boundary is deliberately absent: a line at
    the very left edge of a panel reads as a chart artefact.
    """
    return [(start, name) for start, _, name, _ in PRESIDENTS
            if first < start <= last]
