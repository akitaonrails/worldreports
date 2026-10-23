"""Shared timeline of economy-relevant French events (2006-2026), used to
annotate charts.

Each label is deliberately short enough to sit on a panel without pushing its
neighbour off. Sources are recorded per entry in data/SOURCES.yaml and in the
research notes; where a date is contested the entry uses the one the official
publication carries, not the one the press repeated.

Keep the entries sparse per chart: each figure picks the subset relevant to
its panels, because an annotated line with twenty rules on it is a timeline,
not a chart.
"""

# year -> short label used across infographics
EVENTS = {
    2006: "CPE withdrawn after mass protest",
    2007: "Loi TEPA — overtime tax break",
    2008: "Bank rescue: €360bn guarantee",
    2009: "Recession: GDP −2.6%",
    2010: "Pension age 60 → 62",
    2011: "Fillon austerity plan",
    2012: "CICE created (labour-cost credit)",
    2013: "Employment-security law (ANI)",
    2014: "Pacte de responsabilité",
    2015: "Loi Macron; November attacks",
    2016: "Loi travail, forced through by 49.3",
    2017: "Flat tax on capital; ISF → IFI",
    2018: "Gilets jaunes: €10.3bn package",
    2019: "CICE becomes a contribution cut",
    2020: "COVID-19: GDP −7.9%, deficit 9.2%",
    2021: "Post-COVID rebound: GDP +6.8%",
    2022: "Energy shock: inflation 5.2%",
    2023: "Pension age raised to 64 (49.3)",
    2024: "Dissolution; Barnier censured",
    2025: "Bayrou falls; S&P cuts to A+",
    2026: "2026 budget passed by 49.3",
}

# Precise (year.fraction) markers for line charts, where a rule belongs
# between two years rather than on one.
MARKS = {
    "crisis": (2008.75, "Global financial crisis"),
    "euro_crisis": (2011.6, "Euro sovereign-debt crisis"),
    "covid": (2020.1, "COVID-19"),
    "cice": (2019.0, "CICE becomes a contribution cut"),
    "energy": (2022.2, "Energy price shock"),
    "dissolution": (2024.45, "2024: dissolution"),
}
