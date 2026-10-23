"""Shared timeline of economy-relevant Taiwan events (2006-2026), used to
annotate charts.

Skeleton committed early; entries are finalised as each plate group lands.
Keep the entries sparse per chart: each figure picks the subset relevant
to its panels.

One deliberate absence: COVID-19 gets NO band and no mark on the GDP
plate — 2020 grew +3.42% with no negative quarter anywhere in the
current vintage (country.yaml explains it; the absence is the finding).
"""

# year -> short label used across infographics
EVENTS = {
    2008: "Exports fall ~40% y/y — worst quarter −7.9%",
    2009: "Recession: GDP −1.6%",
    2010: "ECFA signed with mainland China",
    2020: "COVID-19: no contraction — GDP +3.4%",
    2023: "AI demand: exports turn down, then up",
}

# Precise (year.fraction) markers for line charts, where a rule belongs
# between two years rather than on one.
MARKS = {
    "crisis": (2008.75, "global financial crisis"),
    "ecfa": (2010.5, "ECFA"),
    "covid": (2020.1, "COVID-19"),
}
