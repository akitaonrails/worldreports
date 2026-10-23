"""Shared timeline of economy-relevant Canadian events (2006-2026), used to
annotate charts.

Each label is deliberately short enough to sit on a panel without pushing its
neighbour off. Keep the entries sparse per chart: each figure picks the subset
relevant to its panels, because an annotated line with twenty rules on it is a
timeline, not a chart.

One deliberate absence: the 2015 oil-price contraction is an EVENT, not a
band. It met the two-quarter rule, employment never fell, and the Bank of
Canada declined to call it a recession — country.yaml explains why it is not
banded across every plate.
"""

# year -> short label used across infographics
EVENTS = {
    2008: "Bank of Canada cuts to the floor",
    2009: "Recession: GDP −2.9%",
    2015: "Oil-price contraction — not banded (see DATA_NOTES.md)",
    2017: "BoC retires the USD noon rate",
    2020: "COVID-19: balance −14.8% of GDP",
    2022: "Rate-hike cycle begins",
    2023: "Population +3% — a G7 outlier",
    2024: "Immigration levels reversed",
    2025: "Federal carbon levy removed",
}

# Precise (year.fraction) markers for line charts, where a rule belongs
# between two years rather than on one.
MARKS = {
    "crisis": (2008.75, "Global financial crisis"),
    "oil": (2015.0, "oil-price shock"),
    "covid": (2020.1, "COVID-19"),
    "hikes": (2022.2, "the fastest hikes in decades"),
    "fx_break": (2017.2, "the noon rate is retired"),
    "immigration_reversal": (2024.8, "levels plan reversed"),
    "ccb": (2016.5, "Canada Child Benefit"),
    "permit_cap": (2024.0, "permit cap"),
    "us_tariffs": (2025.1, "US tariffs"),
}
