"""Shared timeline of economy-relevant United Kingdom events (2006-2026).

Each label is deliberately short enough to sit on a panel without pushing
its neighbour off. Keep the entries sparse per chart: each figure picks the
subset relevant to its panels, because an annotated line with twenty rules
on it is a timeline, not a chart.

Two deliberate absences. The **2023–24 technical recession** is a band in
country.yaml, not an event: two consecutive negative quarters (−0.2 and
−0.3) meet the rule, however shallow they look beside 2009 and 2020. The
**2016 post-vote slowdown** is neither: it never produced two negative
quarters in a row on this vintage, so drawing it as a downturn would claim
a recession the data do not show. The referendum is marked as an event on
the panels where the line actually turns (sterling, trade, investment).
"""

# year -> short label used across infographics
EVENTS = {
    2008: "Financial crisis: five negative quarters",
    2010: "Austerity government takes office",
    2016: "EU referendum, 23 June",
    2017: "Article 50 triggered, 29 March",
    2020: "Left the EU; COVID-19",
    2022: "Mini-budget and gilt crisis, 23 September",
    2023: "Shallow two-quarter recession",
    2024: "LFS reweighted; dependants rules tightened",
    2025: "Migration to net-positive-by-2025 pledge",
}

# Precise (year.fraction) markers for line charts, where a rule belongs
# between two years rather than on one.
MARKS = {
    "crisis": (2008.75, "global financial crisis"),
    "covid": (2020.1, "COVID-19"),
    "referendum": (2016.5, "the EU referendum"),
    "brexit": (2020.0, "left the EU"),
    "transition": (2021.0, "transition ended"),
    "pbs": (2021.0, "points-based system begins"),
    "mini_budget": (2022.75, "the mini-budget"),
    "qt_end": (2021.9, "asset purchases ended"),
    "lfs_break": (2024.0, "the LFS is reweighted"),
    "dependants": (2024.2, "dependants restricted"),
    "ltim_admin": (2021.5, "admin-based estimates"),
    "estat_frozen": (2020.0, "Eurostat frozen at 2019"),
    "hbai_seam": (2021.5, "survey integrated with admin data"),
    "customs_break": (2021.0, "customs declarations replace Intrastat"),
    "iris": (2014.6, "MUSE to IRIS"),
    "gold": (2025.0, "gold through Switzerland"),
}
