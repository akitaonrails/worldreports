"""Hong Kong's annotation marks, 2006-2026.

Short labels only: each one sits on a panel beside a note, and a label long
enough to need a second line collides with the one next to it. What is an
event here and what is a band is a deliberate split, recorded in
`country.yaml`: a shaded band is a quarter C&SD measured negative, and
nothing else is shaded. An event is a dated decision or a reopening that the
charts point at, and it is drawn as a rule at a fraction of the year where
the thing happened between two annual observations.

No entry is dated from memory: each is either an observation in a committed
CSV (the 2023 population jump, the 2022 rate cycle, the 2026 Base Rate cut)
or a date the publisher states.
"""

# year -> short label, for reference by a plate
EVENTS = {
    2020: "the border closes",
    2022: "the fifth wave",
    2023: "the border reopens",
    2024: "the bond programme issues",
    2026: "the Base Rate follows the Fed down",
}

# (year.fraction, label) for the rules a plate actually draws.
MARKS = {
    # The Base Rate is the Fed's upper bound plus 50bp, so the hiking cycle
    # arrives in Hong Kong on the Fed's dates, not on a local decision.
    "fed_hikes": (2022.2, "the Fed's hikes arrive"),
    "fed_cuts": (2024.7, "the Fed cuts; so does Hong Kong"),
    # Mid-2023: the year-on-year population change turns +2.6% as the
    # boundary reopens — C&SD 110-01001, not an inference.
    "reopening": (2023.0, "the boundary reopens"),
}
