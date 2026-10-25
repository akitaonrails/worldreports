"""Shared timeline of the Australian events the plates annotate.

Each label is deliberately short enough to sit on a panel without pushing
its neighbour off. A figure picks only the marks that belong to its own
subject: an annotated line with twenty rules on it is a timeline, not a
chart.

One deliberate absence: the 2008–09 global financial crisis is a BAND on
every time-series panel only through the country's own downturn bands, and
Australia had no technical recession then — four quarters of negative
growth never happened. It is therefore an annotation where it matters (the
cash rate, the budget balance) and never a recession stripe, which is the
fact worth keeping.
"""

# year -> short label, for a plain answer to "what happened that year".
EVENTS = {
    2008: "the GFC: the cash rate cut, no recession",
    2011: "the mining boom peaks",
    2013: "mining investment peaks",
    2019: "drought and the first COVID quarter",
    2020: "COVID-19: borders close",
    2022: "the fastest tightening since 1994",
    2023: "net migration peaks",
}

# Precise (year.fraction) rules, for a mark that belongs between two years.
MARKS = {
    "gfc": (2008.7, "GFC: the cash rate cuts"),
    "mining_boom": (2011.4, "mining boom peaks"),
    "borders": (2020.2, "borders close"),
    "hikes": (2022.3, "hikes begin"),
    "census": (2021.4, "2021 Census rebase"),
    "delta": (2021.6, "Delta lockdowns"),
}
