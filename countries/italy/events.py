"""Shared timeline of Italian events (2006–2026), used to annotate plates.

Labels are deliberately short enough to sit on a panel without pushing a
neighbour off. Keep the entries sparse per chart: each plate picks the
subset its panels need — an annotated line with twenty rules on it is a
timeline, not a chart.

One deliberate absence, stated in country.yaml: the 2019 stall. On the
staged namq_10_gdp vintage, 2019 Q3 and Q4 are already negative when the
COVID trough arrives, so the sign run into 2020 is technically
continuous from 2019 Q3. The bands mark the pandemic episode; the stall
is the pre-existing condition and belongs here, as an event, not in a
band drawn behind every plate. The 2013 Q4–2014 Q1 near-third-dip
(−0.1, −0.1, then 0.0) is the same judgement at the other end of the
euro-crisis band: noted on the economy plate, never banded.
"""

# year -> short label, for the timeline strip where one exists
EVENTS = {
    2011: "Spread crisis; Monti government (Nov)",
    2012: "“Whatever it takes” — July",
    2018: "Populist coalition; the spread widens",
    2020: "First Western lockdown — March",
    2021: "PNRR: the EU recovery money",
    2023: "Superbonus curtailed",
    2026: "ECB hike: the DFR back to 2.50%",
}

# Precise (year.fraction) markers for line charts, where a rule belongs
# between two years rather than on one.
MARKS = {
    "monti": (2011.9, "Monti government"),
    "wit": (2012.55, "“whatever it takes”"),
    "stall": (2019.6, "the 2019 stall"),
    "lockdown": (2020.15, "first lockdown"),
    "superbonus": (2020.7, "Superbonus 110%"),
    "pnrr": (2021.3, "PNRR"),
    "census": (2011.0, "2011 census"),
    "nic_rebase": (2026.0, "NIC rebased to 2025=100"),
}
