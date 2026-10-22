"""Shared timeline of economy-relevant events (2006-2026), used to annotate
charts. Sources: verified press/official references collected 2026-10-21
(see data/SOURCES.yaml). Keep entries sparse per chart: each figure picks a
subset relevant to its panels.
"""

# year -> short label used across infographics
EVENTS = {
    2008: "Global crisis",
    2010: "GDP +7.5% (fastest since 1986)",
    2013: "Lava Jato begins (Mar 2014)",
    2014: "Recession begins",
    2015: "S&P cuts Brazil to junk",
    2016: "Spending cap (EC 95) / impeachment",
    2017: "Labor reform",
    2018: "Truckers' strike",
    2019: "Pension reform (EC 103)",
    2020: "COVID-19 / emergency aid",
    2021: "IPCA 10.1%, Selic hikes",
    2022: "Lula beats Bolsonaro (runoff)",
    2023: "New fiscal framework / tax reform EC 132",
    2024: "RS floods / G20 Rio",
    2025: "Selic 15% / US 50% tariffs / COP30",
    2026: "VAT test phase / election year",
}

# precise (year.fraction) markers for line charts
MARKS = {
    "crisis": (2008.75, "Global financial crisis"),
    "recession": (2014.9, "2014-16 recession"),
    "covid": (2020.1, "COVID-19"),
    "reform": (2023.95, "Tax reform approved"),
    "vat": (2026.05, "VAT test phase"),
}
