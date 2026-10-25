"""Paraguay's timeline: the few dates a plate needs to name.

Each label is short enough to sit on a panel without pushing its
neighbour off, and each one records something the staged data cannot say
by itself — a change of definition, a treaty revision, a survey redesign.
Nothing here asserts a cause the CSVs do not carry: the 2019-20 bands say
the two years were negative, and the plate's note says the drought and
the pandemic are context, not measured effect (country.yaml).

One deliberate absence: 2022 at -0.03% is a stagnation, not a recession,
and it is annotated on the growth panel instead of banded. A band on
three hundredths of a point would be an artefact of rounding.
"""

# year -> short label, for a panel that names a year in prose.
EVENTS = {
    2008: "Inflation peaks at 10.2%",
    2011: "The guaraní's strongest year",
    2015: "The guaraní turns, and stays down",
    2017: "EPH to EPHC: the survey is redesigned",
    2019: "2019-20: two negative years",
    2020: "Pandemic",
    2022: "Fertility falls below replacement",
    2024: "Minimum wage raised 22% in guaraníes",
    2025: "Annex C: Itaipú's tariff is revised",
}

# (x, label) markers drawn by add_event, where a rule belongs between two
# years or the label must sit at a height the note does not use.
MARKS = {
    "inflation_peak": (2008.0, "10.2% in 2008: the food-price shock"),
    "fx_turn": (2015.0, "the guaraní turns in 2015"),
    "survey_break": (2017.0, "2017: EPH to EPHC"),
    "stagnation": (2022.0, "-0.03% in 2022: stagnation, not banded"),
    "pandemic": (2020.0, "2020-21: the pandemic in the projection"),
    "replacement": (2022.0, "2.00 in 2022: below replacement"),
    "minimum_wage": (2024.0, "2024: +22% in guaraníes"),
    "annex_c": (2025.0, "2025: Annex C"),
}
