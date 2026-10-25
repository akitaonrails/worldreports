"""The Russian timeline, as the short labels a panel can carry.

Only the moments a plate actually draws are here, and each is drawn once,
on the panel whose line it explains. The 2008-09, 2015-16, 2020-21 and 2022
contractions are deliberately absent: they are recession bands from
`country.yaml`, dated on Rosstat's quarterly physical-volume index and drawn
by `ig.add_recessions`, so repeating them here would draw each crisis twice.

None of these is a claim about a number. Each says what a reader needs in
order to read a break: a price that moved in a fortnight, a statistical
perimeter that moved in a year.
"""

#: (year.fraction, label) — a rule drawn where the event is not a calendar
#: year, or falls inside one.
MARKS = {
    # December 2014: the rouble went from about 32 to about 68 to the
    # dollar inside a fortnight, so the 2015 annual mean (61.3) is the
    # year the devaluation arrived in, not the year it happened.
    "rouble_halving": (2014.9, "December 2014: the rouble halves"),
    # March 2014: Rosstat begins counting Crimea and Sevastopol, which is
    # the 144.0m → 146.7m step in its own population series. Not a
    # demographic event and not drawn as one.
    "annexation": (2014.2, "Crimea counted from 2014"),
}
