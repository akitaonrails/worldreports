"""Venezuela's dated events, for the panels that need a rule on them.

Keep this sparse: an annotated line with twenty rules on it is a timeline, not
a chart. Each figure reads the two or three marks that explain its own turn,
which is why this is a dictionary a plate looks things up in rather than a
banner drawn on every panel.

The recession bands are not here — they live in `country.yaml`, dated off the
annual GDP vintage both publishers agree about (2009–10 and 2014–20; 2013 is
deliberately not banded, because the Fund says +0.1 and the Bank +1.3). What
is here are the events a band cannot carry: the redenominations, the year the
state stopped pricing the currency, the pandemic.

No label here asserts a number that a revision could change. The redenomina-
tion labels are exchange identities, not measurements: 1,000,000 bolívares
soberanos became 1 bolívar digital on 20 August 2018, and the digital replaced
the soberano's name on 1 October 2021 (DATA_NOTES.md has the full table).
"""

# year -> the short label a panel draws beside its rule.
EVENTS = {
    2010: "the bolívar is devalued to 2.58 per dollar",
    2016: "the population peak",
    2018: "1,000,000 BsS = 1 VES",
    2020: "COVID-19",
    2021: "the bolívar digital replaces the soberano",
}

# Precise (year.fraction) markers, for a rule that belongs between two years.
# The fractions are months, not statistics: 20 August 2018 and 1 October 2021.
MARKS = {
    "devaluation": (2010.0, EVENTS[2010]),
    "peak": (2016.0, EVENTS[2016]),
    "redenomination": (2018.55, EVENTS[2018]),
    "covid": (2020.15, EVENTS[2020]),
    "digital": (2021.75, EVENTS[2021]),
}
