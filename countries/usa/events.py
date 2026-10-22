"""Shared timeline of economy-relevant US events (2006-2026).

Each entry is a short label a chart can carry without crowding the series it
annotates. Dates are the ones the responsible body published: NBER for the
business cycle, the Federal Reserve for policy rates, the statute's own
effective date for legislation, the Supreme Court's decision date for a
ruling.

The 2025 and 2026 entries were researched from primary and legal sources in
October 2026 rather than recalled, and two of them are corroborated by this
atlas's own committed data rather than by the reporting alone:

  The 2026 rate increase shows up in `data/macro/fed_funds.csv` as a target
  of 3.75-4.00% against 3.50-3.75% at the end of 2025 — the first increase
  since 2023, with CPI back up to 3.2%.

  The autumn 2025 shutdown shows up in `data/macro/unemployment.csv` as a
  year with eleven months instead of twelve. BLS could not collect the
  October 2025 household survey and says it cannot be collected
  retroactively, so October 2025 has no unemployment rate and never will.
  That is a permanent hole in the series, not a late release, and the plates
  that draw unemployment say so.
"""

# year -> short label used across infographics
EVENTS = {
    2007: "Recession begins (Dec, NBER)",
    2008: "Lehman collapses / TARP",
    2009: "ARRA / recession ends (Jun)",
    2010: "Affordable Care Act / Dodd-Frank",
    2011: "Debt-ceiling crisis / S&P downgrade",
    2013: "16-day shutdown",
    2017: "Tax Cuts and Jobs Act",
    2018: "Section 301 tariffs on China",
    2020: "COVID-19 recession / CARES Act",
    2021: "American Rescue Plan / expanded CTC",
    2022: "Fed liftoff / CPI peaks 9.1%",
    2023: "SVB fails / Fiscal Responsibility Act",
    2024: "Fed begins cutting (Sep)",
    2025: "43-day shutdown, the longest ever",
    2026: "IEEPA tariffs struck down / Fed hikes",
}

# Precise (year.fraction) markers, for line charts where the month matters.
# A fraction is the month's midpoint: 2008.70 is mid-September 2008.
MARKS = {
    "lehman": (2008.70, "Lehman Brothers fails"),
    "arra": (2009.12, "ARRA signed"),
    "downgrade": (2011.59, "S&P downgrades the US"),
    "tcja": (2017.97, "Tax Cuts and Jobs Act"),
    "china_tariffs": (2018.52, "Section 301 tariffs"),
    "cares": (2020.24, "CARES Act"),
    "arp": (2021.19, "American Rescue Plan"),
    "liftoff": (2022.20, "Fed liftoff"),
    "cpi_peak": (2022.46, "CPI peaks at 9.1%"),
    "ira": (2022.62, "IRA and CHIPS Acts"),
    "svb": (2023.19, "SVB fails"),
    "first_cut": (2024.72, "first rate cut"),
    "shutdown": (2025.75, "43-day shutdown begins"),
    "ieepa": (2026.14, "Supreme Court strikes down IEEPA tariffs"),
    "section122": (2026.15, "10% Section 122 surcharge"),
}

# Spans worth shading on their own, beyond the two NBER recessions in
# style.RECESSIONS. The 2025-26 funding lapses are drawn as one band
# because on an annual chart they are one episode.
SPANS = {
    "zirp": (2008.95, 2015.95, "policy rate at zero"),
    "zirp_covid": (2020.20, 2022.15, "policy rate at zero"),
    "hiking": (2022.20, 2023.58, "Fed hiking cycle"),
    "shutdowns": (2025.75, 2026.33, "funding lapses"),
}

# The breaks that must be annotated wherever the series they belong to is
# drawn. Smoothing any of these would turn a change in how a number is made
# into a change in the thing being measured.
BREAKS = {
    "education_outlays": (
        2023, "FY2023 reads -$2.2bn: the student-loan forgiveness accrual "
              "booked in FY2022 was reversed, not spent"),
    "student_delinquency": (
        2025, "reporting resumes after the pandemic pause — a reporting "
              "change, not a change in borrowers"),
    "population_vintage": (
        2020, "2020 Census re-bases the estimate; growth across this line "
              "is not comparable"),
    "unemployment_2025": (
        2025, "11 months: October 2025 was never collected"),
    "covid_basis": (
        2020, "underlying cause before, deaths involving after — a "
              "different measure, not a jump"),
}
