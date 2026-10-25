"""Chile's timeline, 2006-2026, for the annotations the plates draw.

Each label is short enough to sit on a panel without pushing its neighbour
off, and a plate picks only the marks that bear on its own panels: a line
with twenty rules on it is a timeline, not a chart.

The two contractions of the window (2009, 2020) are recession BANDS, not
events — they come from country.yaml and `add_recessions`. What is here is
what a band cannot say: the earthquake that started the 2010-12
reconstruction, the copper price that peaked in 2011, the October 2019
social outburst that ended a decade of quiet growth, and the tightening
that answered the 2022 inflation.
"""

# year -> short label, for a rule placed on the year.
EVENTS = {
    2010: "27F: the 8.8 earthquake",
    2011: "copper at its peak",
    2019: "estallido social, October",
    2020: "the pandemic",
    2022: "inflation peaks at 11.6%",
}

# Precise (year.fraction) markers, where the rule belongs inside the year
# rather than on its tick. 27 February 2010 is 0.16 into the year; the
# outburst began on 18 October 2019, 0.80 into it.
MARKS = {
    "quake": (2010.16, "27F: the 8.8 earthquake"),
    "copper": (2011.10, "copper at its peak"),
    "estallido": (2019.80, "estallido social"),
    "pandemic": (2020.20, "the pandemic"),
    "tightening": (2022.90, "the 2022-23 tightening"),
}
