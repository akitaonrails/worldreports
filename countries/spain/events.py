"""Shared timeline of economy-relevant Spanish events (2006-2026), used to
annotate charts.

Each label is deliberately short enough to sit on a panel without pushing its
neighbour off. Keep the entries sparse per chart: each figure picks the subset
relevant to its panels, because an annotated line with twenty rules on it is a
timeline, not a chart.

The three downturn bands are in country.yaml, dated off the quarter-on-quarter
sign of seasonally-adjusted real GDP — see the comment there for the 2011-13
dating debate. The events below are the ones a band cannot carry: a bailout, a
labour reform, a methodology change.
"""

# year -> short label used across infographics
EVENTS = {
    2008: "Property bubble bursts; GDP contracts",
    2010: "First austerity turn; labour reform",
    2012: "Bank bailout (€41bn) · labour reform · deficit −11.5%",
    2013: "Unemployment peaks at 26.1%",
    2014: "Recovery begins; ECB to negative rates",
    2017: "Catalan referendum crisis",
    2020: "COVID-19: GDP −11.2%, the G20's deepest fall",
    2021: "Migration statistics change methodology (EM → EMCR)",
    2022: "Energy shock; IPC peaks at 8.4%",
    2025: "Fertility at 1.10 — among Europe's lowest ever",
    2026: "IPC rebased to base 2025",
}

# Precise (year.fraction) markers for line charts, where a rule belongs
# between two years rather than on one.
MARKS = {
    "crisis": (2008.75, "global financial crisis"),
    "bailout": (2012.45, "bank bailout, June 2012"),
    "whatever_it_takes": (2012.55, "“whatever it takes”"),
    "covid": (2020.1, "COVID-19"),
    "emcr_seam": (2021.0, "EM → EMCR methodology change"),
    "catalan": (2017.75, "Catalan referendum"),
    "hikes": (2022.5, "ECB hikes"),
}
