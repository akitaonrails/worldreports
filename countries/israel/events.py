"""Shared timeline of Israel-relevant events (2006-2026), used to annotate
charts. Labels stay short so a rule and its caption fit a spine panel.

Two deliberate refusals, both checked in country.yaml and pinned by tests:

- The 2008-09 world crisis is not a band here. The staged WEO vintage —
  the only annual growth series in this checkout — shows Israel at +3.2
  (2008) and +1.2 (2009): no contraction year to band. The crisis still
  shows in the data (the shekel, the TA-125, the 2009 deficit), so it is
  annotated where it is visible, not banded everywhere.
- The war years after 7 October 2023 are events, not a band. Annual
  growth stayed positive (+2.0, +1.7, +3.5), so a band would assert a
  contraction the staged series does not show. What the war does to the
  books — revenue 34.6% of GDP in 2024 against expenditure 43.7%, debt
  61.9 -> 67.7 -> 67.9% — is drawn as events and notes on the fiscal
  plate. The October-7 files in the police murder count are annotated on
  the security plate as the data saying it.
"""

# year -> short label used across infographics
EVENTS = {
    2009: "Global crisis: Israel kept growing (+1.2%) — no band",
    2020: "COVID-19: the one contraction year (-1.9%)",
    2022: "Ukraine-war aliyah wave: 76,601 new olim",
    2023: "7 October: war years annotated, never banded",
    2024: "War budget: debt back to 67.7% of GDP",
}

# Precise (year.fraction) markers for line charts, where a rule belongs
# between two years rather than on one.
MARKS = {
    "covid": (2020.1, "COVID-19"),
    "ukraine": (2022.2, "Ukraine-war aliyah wave"),
    "oct7": (2023.75, "the 7 October attack"),
    "war_budget": (2024.0, "the war budget"),
}
