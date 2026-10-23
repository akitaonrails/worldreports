"""Shared timeline of China-relevant events (2006-2026), used to annotate charts.

Each label is deliberately short enough to sit on a panel without pushing its
neighbour off. Keep the entries sparse per chart: each figure picks the subset
relevant to its panels, because an annotated line with twenty rules on it is a
timeline, not a chart.

One deliberate absence: China has NO recession band in this window (country.yaml
carries bands: [] and DATA_NOTES.md pins why — every staged annual real-GDP year
is positive, trough +2.3% in 2020). The 2020 shock and the 2022 and 2024-25
slowdowns therefore ride on the plates as EVENTS, never as bands.
"""

# year -> short label used across infographics
EVENTS = {
    2008: "Global crisis: exports collapse",
    2009: "Four-trillion-yuan stimulus",
    2015: "Equity crash; 811 devaluation",
    2018: "US tariffs begin",
    2020: "COVID-19: +2.3%, still positive",
    2021: "Evergrande default",
    2022: "Zero-COVID lockdowns: +3.0%",
    2024: "Property slump deepens",
}

# Precise (year.fraction) markers for line charts, where a rule belongs
# between two years rather than on one.
MARKS = {
    "crisis": (2008.75, "global financial crisis"),
    "stimulus": (2009.0, "stimulus"),
    "stock_crash": (2015.5, "equity crash"),
    "devaluation": (2015.65, "811 devaluation"),
    "tariffs": (2018.6, "US tariffs"),
    "covid": (2020.1, "COVID-19"),
    "evergrande": (2021.8, "Evergrande"),
    "zerocovid_end": (2022.95, "zero-COVID ends"),
    "slowdown": (2024.0, "slowdown"),
}
