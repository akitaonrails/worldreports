#!/usr/bin/env python3
"""Refresh the Statistics Canada national series into sidecars.

Usage:  python3 -I countries/canada/fetch/fetch_statcan.py

The twelve spine chapters for Canada were built from the harmonised
publishers while Statistics Canada's platform was serving an outage page
under HTTP 200 (see DATA_NOTES.md). The platform answers again; this is
the national layer that was mapped in HANDOFF.md: each sidecar rides
beside the harmonised file for its slot, and the plates will draw both
lines, labelled, never spliced. Nothing here overwrites a curated file:
every output is a `_from_statcan.csv` sidecar for a person to diff.

The candidate PIDs in HANDOFF.md were checked against the live API
(2026-10-22) and the list below is what answered. Each cube is verified
by metadata before its data is pulled: the cube must exist, be CURRENT,
and carry the expected title, so a PID that quietly points at another
table stops the whole fetch rather than relabelling a plate.

  fetched (pid, CANSIM, title as verified live):
    36-10-0699  —    Gross domestic product, expenditure-based, Canada, annual
                    (real growth, current GDP, exports/imports of goods
                    and services — economy 1 and trade 1-2)
    18-10-0005  326-0021 Consumer Price Index, annual average, not seasonally adjusted
                    (all-items index 2002=100 — economy 3; the inflation
                    rate is the year-over-year change of the index)
    14-10-0327  —    Labour force characteristics by gender and detailed age
                    group, annual (unemployment rate, both sexes total,
                    15+ — economy 4)
    11-10-0134  206-0033 Gini coefficients of adjusted market, total and
                    after-tax income (people 1)
    11-10-0135  206-0041 Low income statistics by age, gender and economic
                    family type (MBM 2018-base and 2023-base, LIM-AT —
                    people 2; the MBM bases are separate columns and are
                    not comparable across each other)
    17-10-0009  051-0005 Population estimates, quarterly (July 1 estimate —
                    demography 1; the only national population vintage that
                    underlies the non-permanent-resident story)
    17-10-0008  051-0004 Estimates of the components of demographic growth,
                    annual (July 1 to June 30 — demography 4)
    13-10-0418  102-4505 Crude birth rate, age-specific fertility rates and
                    total fertility rate (demography 2-3)
    35-10-0068  253-0001 Number, rate and percentage changes in rates of
                    homicide victims (police-reported — security 1)
    13-10-0394  102-0561 Leading causes of death, total population, by age
                    group (death registrations, all ages, both sexes —
                    mortality 1-3 and the big killers)
    38-10-0235  378-0123 Financial indicators of households and NPISHs,
                    national balance sheet accounts (credit market debt to
                    disposable income — credit 1)
    11-10-0065  —    Debt service indicators of households, national balance
                    sheet accounts (actual payments, seasonally adjusted —
                    credit 4)

  dropped candidates and why (verified live against getCubeMetadata):
    12-10-0011  answers as "International merchandise trade ... monthly":
                customs-basis goods only; the trade slots are goods AND
                services on the national-accounts basis, which is the
                36-10-0699 line. Never mix the two on one line.
    11-10-0190  answers as "Market income, government transfers, total
                income, income tax and after-tax income": an income table,
                not the Gini table. The Gini cube is 11-10-0134.
    13-10-0386  answers as "Coroner and medical examiner investigated
                deaths": not the Market Basket Measure table. The MBM
                rates live in 11-10-0135 (and 11-10-0103/0066/0230 are
                thresholds, not rates).
    35-10-0177  answers as "Incident-based crime statistics, by detailed
                violations": the whole Uniform Crime Reporting survey;
                the homicide slot needs 253-0001, the homicide table.
    36-10-0639  answers as "Credit liabilities of households": credit
                amounts in dollars, not a ratio. The debt-to-disposable-
                income ratio is 378-0123.
    33-10-0163  answers as monthly average exchange rates (the 2006-07
                fix for markets slot 3): a markets-chapter job, not one
                of the seven national chapters this pass stages. Kept
                verified for whoever wires markets.
    17-10-0040  answers as "Estimates of the components of international
                migration, quarterly": the non-permanent-resident STOCK is
                17-10-0121 (by type, from 2021) or 17-10-0023 (inactive,
                ends 2022) — the migration chapter's job, and the 2021
                start is too short for the atlas window. Flagged, not fetched.

Shape before cache, always: the outage page arrived under HTTP 200, so a
fetched body must parse as the JSON the WDS endpoint returns, or — for
the full-table zip — carry the zip magic bytes and contain the expected
CSV member, before anything is written to cache. A cached error page is
worse than no cache: it survives the retry that would have fixed it.

Every sidecar is written only after every series has passed its shape
check, its spot value and its cross-check against the staged harmonised
file it rides beside; a fetch that cannot confirm what it pulled writes
nothing. Holes stay blank: nothing is interpolated, spliced or projected.
"""
from __future__ import annotations

import csv
import io
import json
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

NAME = 'Canada'
DIRS = {'intl': 'international', 'macro': 'macro', 'trade': 'trade',
        'credit': 'credit', 'social': 'social'}

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache" / "statcan"
WDS = "https://www150.statcan.gc.ca/t1/wds/rest"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)",
           "Accept": "application/json"}

# pid -> (title must contain, CANSIM id or None if the cube predates the
# CANSIM renumbering, earliest year the sidecar needs). Verified live
# 2026-10-22; a cube that answers differently than this table means the
# fetcher is pointing at someone else's statistic.
CUBES = {
    36100699: ("Gross domestic product, expenditure-based, Canada, annual",
               None, 1981),
    18100005: ("Consumer Price Index, annual average, not seasonally",
               "326-0021", 1981),
    14100327: ("Labour force characteristics by gender and detailed age",
               None, 1976),
    11100134: ("Gini coefficients of adjusted market, total and after-tax",
               "206-0033", 1976),
    11100135: ("Low income statistics by age, gender and economic family",
               "206-0041", 2015),
    17100009: ("Population estimates, quarterly", "051-0005", 1976),
    17100008: ("Estimates of the components of demographic growth, annual",
               "051-0004", 1971),
    13100418: ("Crude birth rate, age-specific fertility rates",
               "102-4505", 1991),
    35100068: ("Number, rate and percentage changes in rates of homicide",
               "253-0001", 1961),
    13100394: ("Leading causes of death, total population, by age group",
               "102-0561", 2000),
    38100235: ("Financial indicators of households and non-profit",
               "378-0123", 1990),
    11100065: ("Debt service indicators of households, national balance",
               None, 1990),
}

# The full-table CSV of 13-10-0394 is ~110 MB unpacked; everything else is
# read into memory without ceremony.
Q = 'Seasonally adjusted at annual rates'

# (sidecar, column, decimals, pid, reference-date kind, dimension filters).
# reference-date kind: 'year'  -> "2019"
#                    'july'    -> "2019-07-01" rows only, keyed by year
#                    'period'  -> "2024/2025", keyed by the starting year
#                    'quarter' -> "2025-10", annualised like the BIS file
SERIES = [
    # economy 1 (and the current-dollar levels trade 1-2 divides by)
    ("{macro}/economy_from_statcan.csv", "gdp_real_growth_pct", 1,
     36100699, 'year',
     {'Prices': 'Chained (2017) dollars percentage change',
      'Estimates': 'Gross domestic product at market prices'}),
    ("{macro}/economy_from_statcan.csv", "gdp_current_musd", 0,
     36100699, 'year',
     {'Prices': 'Current Prices',
      'Estimates': 'Gross domestic product at market prices'}),
    ("{trade}/trade_from_statcan.csv", "exports_gs_musd", 0,
     36100699, 'year',
     {'Prices': 'Current Prices',
      'Estimates': 'Exports of goods and services'}),
    ("{trade}/trade_from_statcan.csv", "imports_gs_musd", 0,
     36100699, 'year',
     {'Prices': 'Current Prices',
      'Estimates': 'Less: imports of goods and services'}),
    # economy 3: the annual-average index level; the % change is a
    # documented conversion, done at curation, never here.
    ("{macro}/economy_from_statcan.csv", "cpi_index_2002", 1,
     18100005, 'year',
     {'GEO': 'Canada', 'Products and product groups': 'All-items'}),
    # economy 4: LFS annual (not seasonally adjusted), both sexes total,
    # 15 years and over — the headline population, not an ILO model.
    ("{macro}/economy_from_statcan.csv", "lfs_unemployment_pct", 1,
     14100327, 'year',
     {'GEO': 'Canada', 'Gender': 'Total - Gender',
      'Age group': '15 years and over',
      'Labour force characteristics': 'Unemployment rate'}),
    # people 1: Statistics Canada's own survey Gini, 0-1 as published,
    # three income concepts. The WB figure is a different definition.
    ("social/gini_from_statcan.csv", "gini_market", 3, 11100134, 'year',
     {'GEO': 'Canada', 'Income concept': 'Adjusted market income'}),
    ("social/gini_from_statcan.csv", "gini_total", 3, 11100134, 'year',
     {'GEO': 'Canada', 'Income concept': 'Adjusted total income'}),
    ("social/gini_from_statcan.csv", "gini_aftertax", 3, 11100134, 'year',
     {'GEO': 'Canada', 'Income concept': 'Adjusted after-tax income'}),
    # people 2: the official line is the Market Basket Measure; each base
    # is its own column and the two are never joined across the rebase.
    ("social/poverty_from_statcan.csv", "mbm_2018_pct", 1, 11100135, 'year',
     {'GEO': 'Canada', 'Persons in low income': 'All persons',
      'Statistics': 'Percentage of persons in low income',
      'Low income lines': 'Market basket measure, 2018 base'}),
    ("social/poverty_from_statcan.csv", "mbm_2023_pct", 1, 11100135, 'year',
     {'GEO': 'Canada', 'Persons in low income': 'All persons',
      'Statistics': 'Percentage of persons in low income',
      'Low income lines': 'Market basket measure, 2023 base'}),
    ("social/poverty_from_statcan.csv", "lim_at_pct", 1, 11100135, 'year',
     {'GEO': 'Canada', 'Persons in low income': 'All persons',
      'Statistics': 'Percentage of persons in low income',
      'Low income lines': 'Low income measure after tax'}),
    # demography 1: the July 1 demographic estimate, the vintage that
    # separates non-permanent residents. Quarterly table; the annual
    # plate point is the July reference.
    ("social/population_from_statcan.csv", "population_july1", 0,
     17100009, 'july', {'GEO': 'Canada'}),
    # demography 4: components of growth, July 1 to June 30, keyed by the
    # starting year (the fiscal-style key the fiscal/ files already use).
    ("social/components_from_statcan.csv", "births", 0, 17100008, 'period',
     {'GEO': 'Canada', 'Components of population growth': 'Births'}),
    ("social/components_from_statcan.csv", "deaths", 0, 17100008, 'period',
     {'GEO': 'Canada', 'Components of population growth': 'Deaths'}),
    ("social/components_from_statcan.csv", "immigrants", 0, 17100008,
     'period',
     {'GEO': 'Canada', 'Components of population growth': 'Immigrants'}),
    ("social/components_from_statcan.csv", "emigrants", 0, 17100008,
     'period',
     {'GEO': 'Canada', 'Components of population growth': 'Emigrants'}),
    ("social/components_from_statcan.csv", "returning_emigrants", 0,
     17100008, 'period',
     {'GEO': 'Canada',
      'Components of population growth': 'Returning emigrants'}),
    ("social/components_from_statcan.csv", "net_emigration", 0, 17100008,
     'period',
     {'GEO': 'Canada', 'Components of population growth': 'Net emigration'}),
    ("social/components_from_statcan.csv", "net_non_permanent_residents", 0,
     17100008, 'period',
     {'GEO': 'Canada',
      'Components of population growth': 'Net non-permanent residents'}),
    # demography 2-3: the published crude birth rate and TFR (calendar
    # registration years), so the plate divides nothing.
    ("social/demography_from_statcan.csv", "birth_rate_per_1000", 1,
     13100418, 'year',
     {'GEO': 'Canada, place of residence of mother',
      'Characteristics': 'Crude birth rate, live births per 1,000 population'}),
    ("social/demography_from_statcan.csv", "total_fertility_rate", 2,
     13100418, 'year',
     {'GEO': 'Canada, place of residence of mother',
      'Characteristics': 'Total fertility rate per female'}),
    # security 1: police-reported victims and the rate StatCan publishes
    # with them — beside UNODC's harmonised count, not in place of it.
    ("social/security_from_statcan.csv", "homicide_count", 0, 35100068,
     'year',
     {'GEO': 'Canada', 'Homicides': 'Number of homicide victims'}),
    ("social/security_from_statcan.csv", "homicide_rate_per_100k", 2,
     35100068, 'year',
     {'GEO': 'Canada',
      'Homicides': 'Homicide rates per 100,000 population'}),
    # mortality 1-3 and the big killers: death registrations, all ages,
    # both sexes, underlying cause. Counts only; crude rates divide by
    # the population file at integration.
    ("social/mortality_from_statcan.csv", "deaths_all_causes", 0, 13100394,
     'year',
     {'GEO': 'Canada, place of residence',
      'Age at time of death': 'Age at time of death, all ages',
      'Sex': 'Both sexes', 'Characteristics': 'Number of deaths',
      'Leading causes of death (ICD-10)':
          'Total, all causes of death [A00-Y89]'}),
    ("social/mortality_from_statcan.csv", "deaths_covid_19", 0, 13100394,
     'year',
     {'GEO': 'Canada, place of residence',
      'Age at time of death': 'Age at time of death, all ages',
      'Sex': 'Both sexes', 'Characteristics': 'Number of deaths',
      'Leading causes of death (ICD-10)':
          'COVID-19 [U07.1, U07.2, U10.9]'}),
    ("social/mortality_from_statcan.csv", "deaths_malignant_neoplasms", 0,
     13100394, 'year',
     {'GEO': 'Canada, place of residence',
      'Age at time of death': 'Age at time of death, all ages',
      'Sex': 'Both sexes', 'Characteristics': 'Number of deaths',
      'Leading causes of death (ICD-10)': 'Malignant neoplasms [C00-C97]'}),
    ("social/mortality_from_statcan.csv", "deaths_diseases_of_heart", 0,
     13100394, 'year',
     {'GEO': 'Canada, place of residence',
      'Age at time of death': 'Age at time of death, all ages',
      'Sex': 'Both sexes', 'Characteristics': 'Number of deaths',
      'Leading causes of death (ICD-10)':
          'Diseases of heart [I00-I09, I11, I13, I20-I51]'}),
    ("social/mortality_from_statcan.csv", "deaths_self_harm", 0, 13100394,
     'year',
     {'GEO': 'Canada, place of residence',
      'Age at time of death': 'Age at time of death, all ages',
      'Sex': 'Both sexes', 'Characteristics': 'Number of deaths',
      'Leading causes of death (ICD-10)':
          'Intentional self-harm (suicide) [X60-X84, Y87.0]'}),
    ("social/mortality_from_statcan.csv", "deaths_assault_homicide", 0,
     13100394, 'year',
     {'GEO': 'Canada, place of residence',
      'Age at time of death': 'Age at time of death, all ages',
      'Sex': 'Both sexes', 'Characteristics': 'Number of deaths',
      'Leading causes of death (ICD-10)':
          'Assault (homicide) [X85-Y09, Y87.1]'}),
    ("social/mortality_from_statcan.csv", "deaths_accidents", 0, 13100394,
     'year',
     {'GEO': 'Canada, place of residence',
      'Age at time of death': 'Age at time of death, all ages',
      'Sex': 'Both sexes', 'Characteristics': 'Number of deaths',
      'Leading causes of death (ICD-10)':
          'Accidents (unintentional injuries) [V01-X59, Y85-Y86]'}),
    ("social/mortality_from_statcan.csv", "deaths_influenza_pneumonia", 0,
     13100394, 'year',
     {'GEO': 'Canada, place of residence',
      'Age at time of death': 'Age at time of death, all ages',
      'Sex': 'Both sexes', 'Characteristics': 'Number of deaths',
      'Leading causes of death (ICD-10)':
          'Influenza and pneumonia [J09-J18]'}),
    # credit 1: credit market debt as a ratio to household disposable
    # income (not to GDP: that is the BIS line beside it). Quarterly,
    # annualised like every other quarterly stock in this repo.
    ("{credit}/household_credit_from_statcan.csv",
     "hh_debt_to_disp_income", 2, 38100235, 'quarter',
     {'Sectors': 'Households and non-profit institutions serving households',
      'Categories': 'Credit market debt to disposable income'}),
    # credit 4: what households actually paid — StatCan's own debt
    # service ratio, seasonally adjusted, beside the BIS ratio built on
    # an assumed maturity. Never the same line.
    ("{credit}/debt_service_from_statcan.csv", "hh_dsr_pct", 2,
     11100065, 'quarter',
     {'Seasonal adjustment': Q, 'Estimates': 'Debt service ratio'}),
    ("{credit}/debt_service_from_statcan.csv", "mortgage_dsr_pct", 2,
     11100065, 'quarter',
     {'Seasonal adjustment': Q,
      'Estimates': 'Mortgage debt service ratio'}),
]

# (sidecar, column, year, value): one known value per series, read off
# the live API on 2026-10-22 — the day the platform answered again after
# the outage, which is exactly the value a rerun must reproduce.
SPOT = [
    ("macro/economy_from_statcan.csv", "gdp_real_growth_pct", 2022, 4.7),
    ("macro/economy_from_statcan.csv", "gdp_current_musd", 2024, 3108551.0),
    ("macro/economy_from_statcan.csv", "cpi_index_2002", 2024, 160.9),
    ("macro/economy_from_statcan.csv", "lfs_unemployment_pct", 2024, 6.3),
    ("trade/trade_from_statcan.csv", "exports_gs_musd", 2024, 1009319.0),
    ("trade/trade_from_statcan.csv", "imports_gs_musd", 2024, 1015016.0),
    ("trade/trade_from_statcan.csv", "exports_pct_gdp", 2024, 32.4694),
    ("trade/trade_from_statcan.csv", "imports_pct_gdp", 2024, 32.6524),
    ("social/gini_from_statcan.csv", "gini_market", 2024, 0.436),
    ("social/gini_from_statcan.csv", "gini_total", 2023, 0.346),
    ("social/gini_from_statcan.csv", "gini_aftertax", 2023, 0.301),
    ("social/poverty_from_statcan.csv", "mbm_2018_pct", 2022, 10.3),
    ("social/poverty_from_statcan.csv", "mbm_2023_pct", 2024, 11.0),
    ("social/poverty_from_statcan.csv", "lim_at_pct", 2023, 12.1),
    ("social/population_from_statcan.csv", "population_july1", 2024, 41162593.0),
    ("social/components_from_statcan.csv", "births", 2023, 362014.0),
    ("social/components_from_statcan.csv", "deaths", 2023, 330185.0),
    ("social/components_from_statcan.csv", "immigrants", 2024, 435551.0),
    ("social/components_from_statcan.csv", "emigrants", 2023, 107876.0),
    ("social/components_from_statcan.csv", "returning_emigrants", 2023, 48386.0),
    ("social/components_from_statcan.csv", "net_emigration", 2023, 59490.0),
    ("social/components_from_statcan.csv", "net_non_permanent_residents", 2023, 703206.0),
    ("social/demography_from_statcan.csv", "birth_rate_per_1000", 2024, 8.9),
    ("social/demography_from_statcan.csv", "total_fertility_rate", 2024, 1.26),
    ("social/security_from_statcan.csv", "homicide_count", 2024, 797.0),
    ("social/security_from_statcan.csv", "homicide_rate_per_100k", 2024, 1.93),
    ("social/mortality_from_statcan.csv", "deaths_all_causes", 2024, 326779.0),
    ("social/mortality_from_statcan.csv", "deaths_covid_19", 2022, 19948.0),
    ("social/mortality_from_statcan.csv", "deaths_malignant_neoplasms", 2024, 85589.0),
    ("social/mortality_from_statcan.csv", "deaths_diseases_of_heart", 2024, 57982.0),
    ("social/mortality_from_statcan.csv", "deaths_self_harm", 2024, 3852.0),
    ("social/mortality_from_statcan.csv", "deaths_assault_homicide", 2024, 454.0),
    ("social/mortality_from_statcan.csv", "deaths_accidents", 2024, 20415.0),
    ("social/mortality_from_statcan.csv", "deaths_influenza_pneumonia", 2024, 7658.0),
    ("credit/household_credit_from_statcan.csv",
     "hh_debt_to_disp_income_q4", 2025, 171.89),
    ("credit/household_credit_from_statcan.csv",
     "hh_debt_to_disp_income_qavg", 2025, 170.85),
    ("credit/household_credit_from_statcan.csv",
     "hh_debt_to_disp_income_quarters", 2025, 4.0),
    ("credit/debt_service_from_statcan.csv", "hh_dsr_pct_q4", 2025, 14.68),
    ("credit/debt_service_from_statcan.csv", "hh_dsr_pct_qavg", 2025, 14.71),
    ("credit/debt_service_from_statcan.csv", "hh_dsr_pct_quarters", 2025, 4.0),
    ("credit/debt_service_from_statcan.csv", "mortgage_dsr_pct_q4", 2025, 7.83),
    ("credit/debt_service_from_statcan.csv", "mortgage_dsr_pct_qavg", 2025, 7.88),
    ("credit/debt_service_from_statcan.csv", "mortgage_dsr_pct_quarters", 2025, 4.0),
]

# (label, StatCan rel, column, year, harmonised file, column, scale,
# tolerance): the national number against the staged harmonised twin it
# will ride beside. A tolerance of None marks a pair that differs by
# definition — printed for the record, not asserted.
CROSS = [
    ('Real GDP growth (StatCan vs WB redistribution)',
     'macro/economy_from_statcan.csv', 'gdp_real_growth_pct', 2019,
     'macro/growth_prices_from_wb.csv', 'real_growth_pct', 1, ('abs', 0.5)),
    ('LFS unemployment vs ILO modelled',
     'macro/economy_from_statcan.csv', 'lfs_unemployment_pct', 2019,
     'macro/economy_from_wb.csv', 'unemployment_pct', 1, ('abs', 0.5)),
    ('Exports of goods and services (StatCan GDP vs WB)',
     'trade/trade_from_statcan.csv', 'exports_pct_gdp', 2019,
     'trade/trade_from_wb.csv', 'exports_pct_gdp', 1, ('abs', 1.5)),
    ('Imports of goods and services (StatCan GDP vs WB)',
     'trade/trade_from_statcan.csv', 'imports_pct_gdp', 2019,
     'trade/trade_from_wb.csv', 'imports_pct_gdp', 1, ('abs', 1.5)),
    ('Population July 1 vs WB annual (SP.POP.TOTL)',
     'social/population_from_statcan.csv', 'population_july1', 2021,
     'international/population.csv', 'population', 1, ('rel', 0.005)),
    ('Crude birth rate (registration vs UN estimate)',
     'social/demography_from_statcan.csv', 'birth_rate_per_1000', 2019,
     'social/demography_from_wb.csv', 'birth_rate_per_1000', 1, ('abs', 0.6)),
    ('Total fertility rate (registration vs UN estimate)',
     'social/demography_from_statcan.csv', 'total_fertility_rate', 2019,
     'social/demography_from_wb.csv', 'fertility', 1, ('abs', 0.12)),
    ('All-cause deaths (registrations vs OECD reprint)',
     'social/mortality_from_statcan.csv', 'deaths_all_causes', 2020,
     'social/causes_of_death_from_oecd.csv', 'deaths', 1, ('rel', 0.02)),
    ('Homicide (police-reported vs UNODC)',
     'social/security_from_statcan.csv', 'homicide_rate_per_100k', 2021,
     'social/security_from_wb.csv', 'homicide_per_100k', 1, None),
    ('Household debt (to disposable income vs BIS to GDP)',
     'credit/household_credit_from_statcan.csv',
     'hh_debt_to_disp_income_q4', 2019,
     'credit/household_credit_from_bis.csv', 'hh_credit_pct_gdp_q4', 1, None),
    ('Debt service ratio (actual payments vs BIS modelled)',
     'credit/debt_service_from_statcan.csv', 'hh_dsr_pct_q4', 2019,
     'credit/debt_service_from_bis.csv', 'hh_dsr_pct_q4', 1, None),
]

FIRST_YEAR, LAST_YEAR = 1961, 2026


class FetchError(RuntimeError):
    pass


# --------------------------------------------------------------- transport
def get(url: str, cache_name: str, check, body: bytes | None = None) -> bytes:
    """The body at `url`, validated by `check` BEFORE it is cached.

    A cached error page is worse than no cache: it survives the retry
    that would have fixed it, and this endpoint served an HTML apology
    under HTTP 200 for a day. So the check runs on the way in, and again
    on a cached copy left by an older run, which is thrown away if it
    fails.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / cache_name
    if path.exists():
        raw = path.read_bytes()
        try:
            check(raw)
            return raw
        except Exception as e:  # noqa: BLE001
            print(f"  stale cache {cache_name}: {e}", file=sys.stderr)
            path.unlink()
    last: Exception | None = None
    for attempt in range(4):
        try:
            headers = dict(HEADERS)
            if body is not None:
                # WDS answers 415 unless the POST says it carries JSON.
                headers["Content-Type"] = "application/json"
            req = urllib.request.Request(url, data=body, headers=headers)
            with urllib.request.urlopen(req, timeout=240) as r:
                raw = r.read()
            check(raw)
            path.write_bytes(raw)
            return raw
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"  {cache_name} attempt {attempt + 1}: {e}", file=sys.stderr)
            time.sleep(3 * (attempt + 1))
    raise FetchError(f"{url}: {last}")


def json_ok(raw: bytes):
    """WDS answers with JSON. The outage page was HTML under HTTP 200."""
    try:
        return json.loads(raw)
    except ValueError:
        raise ValueError(f"not JSON: {raw[:80]!r}")


def meta_ok(raw: bytes, pid: int):
    """One cube's metadata, cross-checked against the CUBES table."""
    got = json_ok(raw)
    if not (isinstance(got, list) and got and got[0].get("status") == "SUCCESS"):
        raise ValueError(f"metadata call failed: {str(got)[:120]}")
    cube = got[0]["object"]
    title, cansim, first = CUBES[pid]
    if title not in cube["cubeTitleEn"]:
        raise ValueError(f"{pid} is not the expected cube: {cube['cubeTitleEn']!r}")
    if "CURRENT" not in cube.get("archiveStatusEn", ""):
        raise ValueError(f"{pid} is not CURRENT: {cube.get('archiveStatusEn')!r}")
    if cansim and cube.get("cansimId") != cansim:
        raise ValueError(f"{pid} carries CANSIM id {cube.get('cansimId')!r}, "
                         f"expected {cansim!r}")
    if int(cube["cubeStartDate"][:4]) > first:
        raise ValueError(f"{pid} starts {cube['cubeStartDate']}, needed from {first}")
    return cube


def download_ok(raw: bytes, pid: int):
    got = json_ok(raw)
    if not (isinstance(got, dict) and got.get("status") == "SUCCESS"
            and str(got.get("object", "")).startswith("https://")):
        raise ValueError(f"download call failed: {str(got)[:120]}")
    if got["object"] != (f"https://www150.statcan.gc.ca/n1/tbl/csv/"
                         f"{pid}-eng.zip"):
        raise ValueError(f"{pid} points at an unexpected URL: {got['object']}")
    return got["object"]


def zip_ok(raw: bytes, pid: int):
    """A full-table download must be a zip holding the cube's CSV member."""
    if raw[:4] != b"PK\x03\x04":
        raise ValueError(f"not a zip: {raw[:80]!r}")
    try:
        names = zipfile.ZipFile(io.BytesIO(raw)).namelist()
    except zipfile.BadZipFile as e:
        raise ValueError(f"bad zip: {e}")
    if f"{pid}.csv" not in names:
        raise ValueError(f"zip holds {names}, not {pid}.csv")


# --------------------------------------------------------------- cubes
def cube_rows(pid: int) -> list[dict]:
    """Every row of one cube's full-table CSV, after both endpoints have
    been shape-checked and the cube's metadata has been verified."""
    get(f"{WDS}/getCubeMetadata", f"{pid}_meta.json",
        lambda raw: meta_ok(raw, pid),
        body=json.dumps([{"productId": pid}]).encode())
    url = download_ok(get(f"{WDS}/getFullTableDownloadCSV/{pid}/en",
                          f"{pid}_download.json",
                          lambda raw: download_ok(raw, pid)), pid)
    raw = get(url, f"{pid}.zip", lambda raw: zip_ok(raw, pid))
    text = zipfile.ZipFile(io.BytesIO(raw)).read(f"{pid}.csv").decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def ref_year(kind: str, ref: str) -> int | None:
    if kind == 'year':
        return int(ref[:4])
    if kind == 'july':                       # "2024-07-01" — July 1 only
        return int(ref[:4]) if ref[5:7] == '07' else None
    if kind == 'period':                     # "2024/2025" — keyed by start
        return int(ref.split('/')[0])
    if kind == 'quarter':
        return int(ref[:4])
    raise ValueError(kind)


def quarter_of(kind: str, ref: str) -> int | None:
    return ((int(ref[5:7]) - 1) // 3 + 1) if kind == 'quarter' else None


def collect() -> dict[str, dict[int, dict[str, float]]]:
    tables: dict[str, dict[int, dict[str, float]]] = {}
    decimals: dict[tuple[str, str], int] = {}
    order: dict[str, list[str]] = {}
    by_cube: dict[int, list[dict]] = {}
    quarters: dict[tuple[str, str], dict[str, float]] = {}

    rel_of = lambda t: t.format(**DIRS) if '{' in t else t

    for rel_t, column, dec, pid, kind, filters in SERIES:
        rel = rel_of(rel_t)
        if pid not in by_cube:
            print(f"Statistics Canada {str(pid)[:2]}-{str(pid)[2:4]}-"
                  f"{str(pid)[4:]}  ({CUBES[pid][0][:50]}...)")
            by_cube[pid] = cube_rows(pid)
        series: dict[int, float] = {}
        for x in by_cube[pid]:
            if not (x['VALUE'] and all(x[k] == v for k, v in filters.items())):
                continue
            y = ref_year(kind, x['REF_DATE'])
            if y is None or not FIRST_YEAR <= y <= LAST_YEAR:
                continue
            key = x['REF_DATE'] if kind == 'quarter' else y
            if key in series:
                raise FetchError(f"{pid}: {column} twice for {key}")
            series[key] = float(x['VALUE'])
        if not series:
            raise FetchError(f"{pid}: {column} came back empty — the cube's "
                             "dimension labels changed under the fetcher")
        n = len(series)
        if kind == 'quarter':
            quarters[(rel, column)] = series
            print(f"  {column:<28} {n:>4} quarters "
                  f"{min(series)}..{max(series)}")
        else:
            t = tables.setdefault(rel, {})
            for y, value in series.items():
                t.setdefault(y, {})[column] = value
            decimals[(rel, column)] = dec
            order.setdefault(rel, []).append(column)
            print(f"  {column:<28} {n:>4} years "
                  f"{min(series)}-{max(series)}")

    # Quarterly stocks join the house convention: year-end (Q4) value,
    # the mean of the quarters published, and how many, so a running
    # year reads as its quarters and never as a year's result.
    for (rel, column), series in quarters.items():
        by_year: dict[int, dict[int, float]] = {}
        for ref, value in series.items():
            by_year.setdefault(int(ref[:4]), {})[quarter_of('quarter', ref)] = value
        for year, qs in by_year.items():
            row = tables.setdefault(rel, {}).setdefault(year, {})
            row[f"{column}_qavg"] = sum(qs.values()) / len(qs)
            row[f"{column}_quarters"] = float(len(qs))
            if 4 in qs:
                row[f"{column}_q4"] = qs[4]
        for col in (f"{column}_q4", f"{column}_qavg", f"{column}_quarters"):
            decimals[(rel, col)] = 0 if col.endswith('quarters') else 2
            order.setdefault(rel, []).append(col)

    # The trade slots want % of GDP; the sidecar holds the published
    # current-dollar millions and the ratio is computed here once, from
    # the same cube and vintage, and kept in the trade file beside them.
    gdp = tables['macro/economy_from_statcan.csv']
    trade = tables['trade/trade_from_statcan.csv']
    for y, row in trade.items():
        g = gdp.get(y, {}).get('gdp_current_musd')
        if not g:
            continue
        row['exports_pct_gdp'] = 100.0 * row['exports_gs_musd'] / g
        row['imports_pct_gdp'] = 100.0 * row['imports_gs_musd'] / g
    for col in ('exports_pct_gdp', 'imports_pct_gdp'):
        decimals[('trade/trade_from_statcan.csv', col)] = 2
        order['trade/trade_from_statcan.csv'].append(col)

    collect.decimals = decimals  # type: ignore[attr-defined]
    collect.order = order        # type: ignore[attr-defined]
    return tables


# --------------------------------------------------------------- checks
def spot_checks(tables) -> None:
    """A known value per series. A refetch that moves one fails loudly."""
    bad = []
    for rel, column, year, want in SPOT:
        got = tables.get(rel, {}).get(year, {}).get(column)
        if got is None or abs(got - want) > max(abs(want) * 0.03, 0.1):
            bad.append(f"{rel} {column} {year}: want {want}, got {got}")
    covered = {(rel, c) for rel, c, _, _ in SPOT}
    missing = [f"{rel} {c}" for rel, cols in collect.order.items()
               for c in cols if (rel, c) not in covered]
    if missing:
        bad.append(f"no spot value asserted for {missing}")
    if bad:
        raise FetchError("spot checks failed:\n  " + "\n  ".join(bad))
    print(f"Spot checks: {len(SPOT)} values as expected")


def staged(rel: str, column: str, year: int) -> float | None:
    """One cell of a staged file of this country (curated or sidecar)."""
    path = DATA / rel
    if not path.exists():
        return None
    with path.open(encoding="utf-8", newline="") as fh:
        lines = [ln for ln in fh if not ln.lstrip().startswith("#")]
    for row in csv.DictReader(lines):
        key = row.get("year") or row.get("fiscal_year")
        if key == str(year) and (row.get(column) or "").strip():
            return float(row[column])
    return None


def cross_checks(tables) -> None:
    """The national number against its harmonised twin, where both exist."""
    bad = []
    print("Cross-checks against the staged harmonised series")
    for label, rel, column, year, hrel, hcol, scale, tol in CROSS:
        nat = tables[rel][year][column] * scale
        har = staged(hrel, hcol, year)
        if har is None:
            bad.append(f"{label}: no staged value {hrel}:{hcol} {year}")
            continue
        verdict = "printed only (different definitions)"
        if tol is not None:
            kind, limit = tol
            diff = abs(nat - har) / abs(har) if kind == "rel" else abs(nat - har)
            verdict = f"{'ok' if diff <= limit else 'FAIL'} " \
                      f"({kind} {diff:.3f} <= {limit})"
            if diff > limit:
                bad.append(f"{label} {year}: national {nat:.4g} "
                           f"vs staged {har:.4g}")
        print(f"  {label} {year}: national {nat:,.4g} | "
              f"{hrel}:{hcol} {har:,.4g} — {verdict}")
    if bad:
        raise FetchError("cross-checks failed:\n  " + "\n  ".join(bad))


# --------------------------------------------------------------- output
def write(tables) -> None:
    for rel in sorted(tables):
        columns = collect.order[rel]
        path = DATA / rel
        header = ",".join(["year", *columns])
        if path.exists():
            first = next((ln for ln in path.read_text().splitlines()
                          if not ln.startswith("#")), "")
            if first != header:
                raise FetchError(f"refusing to overwrite {rel}: it holds "
                                 f"{first!r}, not this fetcher's sidecar")
        lines = [header]
        for year in sorted(tables[rel]):
            row = tables[rel][year]
            cells = []
            for c in columns:
                v = row.get(c)
                cells.append("" if v is None else
                             f"{v:.{collect.decimals[(rel, c)]}f}")
            if any(cells):
                lines.append(f"{year}," + ",".join(cells))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n")
        print(f"  data/{rel}  {len(lines) - 1} rows, {len(columns)} columns")


def main() -> None:
    print(f"Statistics Canada national series for {NAME}")
    try:
        tables = collect()
        spot_checks(tables)
        cross_checks(tables)
    except FetchError as e:
        print(f"!! {e}\nNothing written.", file=sys.stderr)
        sys.exit(1)
    write(tables)
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
