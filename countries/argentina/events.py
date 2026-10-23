"""Shared timeline of economy-relevant events (2006-2026), used to annotate
charts. Keep entries sparse per chart: each figure picks a subset relevant
to its panels.

Argentina's twenty years are punctuated by policy breaks rather than by the
business cycle alone, and several of them are breaks in the *data* as well
as in the economy — the 2007 intervention of INDEC above all. Where that is
true the chart says so on the panel instead of drawing through it.
"""

# year -> short label used across infographics
EVENTS = {
    2006: "IMF debt paid off in full (US$9.5bn)",
    2007: "INDEC intervened — official CPI breaks",
    2008: "Resolution 125 farm conflict; pensions renationalised",
    2009: "Global crisis + drought",
    2010: "Second debt exchange (92% accepted)",
    2011: "Cepo cambiario — FX controls imposed",
    2012: "YPF expropriated",
    2014: "Selective default on holdouts; January devaluation",
    2015: "Macri elected; cepo lifted (Dec)",
    2016: "Statistical emergency; new national CPI (Dec)",
    2017: "Return to international markets",
    2018: "Currency run; IMF stand-by (US$57bn)",
    2019: "Debt 'reperfilamiento'; cepo returns",
    2020: "COVID-19; foreign debt restructured",
    2022: "IMF Extended Fund Facility",
    2023: "Historic drought; Milei elected; 118% devaluation (Dec)",
    2024: "First primary surplus since 2010; disinflation",
    2025: "Cepo lifted for individuals (Apr); new IMF EFF (US$20bn)",
    2026: "Partial year",
}

# precise (year.fraction) markers for line charts
MARKS = {
    "indec": (2007.05, "INDEC intervened"),
    "crisis": (2008.75, "Global financial crisis"),
    "cepo1": (2011.83, "Cepo cambiario"),
    "default": (2014.58, "Holdout default"),
    "cepo_off": (2015.96, "Cepo lifted"),
    "ipc_new": (2016.96, "New national CPI"),
    "imf": (2018.5, "IMF stand-by"),
    "cepo2": (2019.66, "Cepo returns"),
    "covid": (2020.2, "COVID-19"),
    "milei": (2023.96, "Devaluation, 118%"),
    "cepo_off2": (2025.29, "Cepo lifted"),
}

# The stretch where the official consumer price index cannot be used. INDEC
# was intervened in January 2007 and the national CPI only restarts in
# December 2016; the 2016 statistical emergency withdrew what lay between.
# On the plates' annual axis a year is centred on its tick, so the band runs
# from half a year before 2007 to half a year after 2016: it covers exactly
# the ten annual readings 2007-2016 and none either side.
INDEC_GAP = (2006.5, 2016.5)
