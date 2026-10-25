"""Poland's timeline, 2006-2026, as the plates annotate it.

Two rules kept this list short. An event goes in only if a plate draws a
line at it, and each label has to fit beside its own line without pushing
its neighbour off the panel — a chart with a rule on every turning point is
a timeline, not a chart.

Deliberately absent: EU accession (1 May 2004) is outside the window and
lives in the page copy; the 2008-09 crisis is an EVENT, not a band, because
Poland grew through it (4.4% in 2008, 2.6% in 2009) and banding a recession
that did not happen would be a lie drawn across every panel; the 2023
election and the 2015-16 constitutional crisis are political events with no
series that turns at them.
"""

#: year -> the short label a plate may use for it.
EVENTS = {
    2009: "the crisis Poland grew through",
    2012: "the population turns down",
    2015: "the franc peg is dropped",
    2016: "Family 500+ begins",
    2020: "COVID-19 and the register's hole",
    2021: "the census revises the population",
    2022: "the refugee inflow",
}

#: Precise (year.fraction) markers, where a rule belongs between two years.
MARKS = {
    "crisis": (2008.8, "the crisis Poland grew through"),
    "franc": (2015.04, "the SNB drops the franc peg"),
    "family": (2016.25, "Family 500+ begins"),
    "hikes": (2021.75, "the NBP starts hiking"),
    "census": (2021.0, "the 2021 census revision"),
    "refugees": (2022.15, "the refugee inflow"),
}
