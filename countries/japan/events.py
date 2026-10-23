"""Shared timeline of economy-relevant Japanese events (2006-2026), used to
annotate charts.

Each label is deliberately short enough to sit on a panel without pushing
its neighbour off. Keep the entries sparse per chart: each figure picks the
subset relevant to its panels, because an annotated line with twenty rules
on it is a timeline, not a chart.

Three deliberate choices about downturns, all decided against the staged
ESRI quarterly vintage (see country.yaml):

- The **2011 Tohoku earthquake** is an EVENT, not a band of its own. It
  falls inside the 2010 Q4 – 2011 Q2 contraction, which begins a quarter
  BEFORE the quake: the run started on data, and calling the band an
  earthquake would misdate it. ESRI dates no recession here; the band is
  the atlas's own two-quarter rule, and the notes say so.
- The **2024 Q1–Q2 dip** is a band, not an event label (kept on
  2026-10-22 as a user decision). The quarters are −0.09 and −0.12 q/q,
  inside revision noise, so a country test pins both values against the
  staged CSVs: a revision that lifts either quarter fails the build and
  forces the band to be reconsidered, not silently kept.
- The consumption-tax quarters (2014 Q2 −1.4, 2019 Q4 −2.9) are single
  quarters and are marked as EVENTS on the panels they move (tax,
  inflation, consumption), never as bands.
"""

# year -> short label used across infographics
EVENTS = {
    2008: "Global financial crisis",
    2011: "Great East Japan earthquake, 11 March",
    2013: "QQE launched, April",
    2014: "Consumption tax to 8%, April",
    2016: "Negative rate (Jan); yield-curve control (Sep)",
    2019: "Consumption tax to 10%, October",
    2020: "COVID-19: borders close",
    2023: "YCC curve loosened, December",
    2024: "YCC and negative rates end, March",
    2025: "New census base, October",
}

# Precise (year.fraction) markers for line charts, where a rule belongs
# between two years rather than on one.
MARKS = {
    "crisis": (2008.75, "global financial crisis"),
    "quake": (2011.2, "the earthquake, 11 March"),
    "qqe": (2013.25, "QQE begins"),
    "tax14": (2014.25, "consumption tax to 8%"),
    "neg": (2016.0, "negative rate"),
    "ycc": (2016.75, "yield-curve control"),
    "tax19": (2019.75, "consumption tax to 10%"),
    "covid": (2020.1, "COVID-19"),
    "border": (2020.25, "borders close"),
    "border_open": (2022.9, "borders reopen"),
    "ycc_loose": (2023.9, "the YCC curve loosens"),
    "ycc_end": (2024.25, "the YCC ends"),
    "hike": (2024.75, "the rate rises again"),
    "fx_slide": (2022.0, "the yen's slide begins"),
    "residence": (2012.5, "residence-card regime begins"),
    "comp_prot": (2023.9, "complementary protection"),
    "census25": (2025.75, "the 2025 census"),
}
