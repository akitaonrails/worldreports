#!/usr/bin/env python3
"""One-off curation of the StatCan sidecars into national CSVs (this pass only)."""
import csv
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / 'data'

def read(rel):
    with (DATA / rel).open(encoding='utf-8', newline='') as fh:
        return list(csv.DictReader([l for l in fh if not l.lstrip().startswith('#')]))

def fmt(v, dec):
    if v is None or v == '':
        return ''
    return f'{float(v):.{dec}f}'

def emit(rel, header, rows):
    path = DATA / rel
    path.write_text('\n'.join(header + rows) + '\n')
    print(f'  {rel}  {len(rows)-1} rows')

FIRST = 2005

# --- macro/economy_statcan.csv
src = read('macro/economy_from_statcan.csv')
idx = {int(r['year']): r for r in src}
years = sorted(y for y in idx if y >= FIRST)
rows = []
for y in years:
    r = idx[y]
    cpi = float(r['cpi_index_2002']) if r['cpi_index_2002'] else None
    prev = idx.get(y - 1, {}).get('cpi_index_2002')
    infl = (cpi / float(prev) - 1) * 100 if cpi and prev else None
    cells = [r['gdp_real_growth_pct'], fmt(infl, 2), r['lfs_unemployment_pct']]
    if any(c for c in cells):
        rows.append(f"{y}," + ','.join(cells))
emit('macro/economy_statcan.csv', [
 '# Statistics Canada 36-10-0699 (chained-FCE2017 percentage change), 18-10-0005 (CPI annual average, all-items, 2002=100) and 14-10-0327 (LFS, both sexes total, 15+), curated.',
 '# cpi_inflation_pct is the year-over-year per cent change of the published annual-average index: a documented conversion, not a publisher series.',
 '# LFS annual figures are not seasonally adjusted; they are the national line beside the ILO modelled estimate, never spliced with it.',
 'year,real_growth_pct,cpi_inflation_pct,lfs_unemployment_pct'], rows)

# --- trade/trade_statcan.csv
src = read('trade/trade_from_statcan.csv')
rows = []
for r in src:
    if int(r['year']) < FIRST: continue
    cells = [r['exports_pct_gdp'], r['imports_pct_gdp']]
    if any(c for c in cells):
        rows.append(r['year'] + ',' + ','.join(cells))
emit('trade/trade_statcan.csv', [
 '# Statistics Canada 36-10-0699, current-dollar exports/imports of goods and services divided by current-dollar GDP (same cube, same vintage): the national-accounts line beside the World Bank redistribution, never a customs series.',
 '# The balance is their difference and is not stored.',
 'year,exports_pct_gdp,imports_pct_gdp'], rows)

# --- social/gini_statcan.csv
src = read('social/gini_from_statcan.csv')
rows = []
for r in src:
    if int(r['year']) < FIRST: continue
    rows.append(','.join([r['year'], r['gini_market'], r['gini_total'], r['gini_aftertax']]))
emit('social/gini_statcan.csv', [
 '# Statistics Canada 11-10-0134, Gini coefficients on the adjusted-income concept, curated unchanged, 0-1 as published (the plate draws 0-100).',
 '# Statistics Canada\'s own survey Gini is NOT the same quantity as the World Bank or OECD derivations: different income definitions, different populations.',
 'year,gini_market,gini_total,gini_aftertax'], rows)

# --- social/poverty_statcan.csv
src = read('social/poverty_from_statcan.csv')
rows = []
for r in src:
    if int(r['year']) < FIRST: continue
    rows.append(','.join([r['year'], r['mbm_2018_pct'], r['mbm_2023_pct'], r['lim_at_pct']]))
emit('social/poverty_statcan.csv', [
 '# Statistics Canada 11-10-0135, all persons, percentage in low income, curated.',
 '# TWO MBM BASES, TWO COLUMNS, NEVER ONE LINE: the 2018-base series (2015-2023) and the 2023-base series (2020-) measure different thresholds; joining them is a rebase seam.',
 '# The LIM-AT column is a purely relative measure kept beside the official MBM line for context, not a substitute for it.',
 'year,mbm_2018_pct,mbm_2023_pct,lim_at_pct'], rows)

# --- social/population_statcan.csv
src = read('social/population_from_statcan.csv')
rows = [r for r in src if int(r['year']) >= FIRST]
emit('social/population_statcan.csv', [
 '# Statistics Canada 17-10-0009, the July 1 demographic estimate, curated: the national population vintage, and the only one that separates non-permanent residents.',
 '# The 2026 row is the latest published estimate, not a year\'s result.',
 'year,population_july1'],
 [r['year'] + ',' + r['population_july1'] for r in rows])

# --- social/components_statcan.csv
src = read('social/components_from_statcan.csv')
rows = [r for r in src if int(r['year']) >= FIRST]
cols = ['births', 'deaths', 'immigrants', 'emigrants', 'returning_emigrants',
        'net_emigration', 'net_non_permanent_residents']
emit('social/components_statcan.csv', [
 '# Statistics Canada 17-10-0008, components of demographic growth, curated unchanged.',
 '# year is the STARTING year of a July 1 to June 30 period: 2024 is 2024-07-01 to 2025-06-30, like the fiscal files\' convention. Calendar rates (crude birth rate) live in demography_statcan.csv instead.',
 '# net_emigration = emigrants minus returning emigrants; the components are published separately and nothing here adds or nets them.',
 'year,' + ','.join(cols)],
 [r['year'] + ',' + ','.join(r[c] for c in cols) for r in rows])

# --- social/demography_statcan.csv
src = read('social/demography_from_statcan.csv')
rows = [r for r in src if int(r['year']) >= FIRST]
emit('social/demography_statcan.csv', [
 '# Statistics Canada 13-10-0418, crude birth rate and total fertility rate (live births, calendar registration years), curated unchanged.',
 '# The crude death rate has no published national series in this cube; integration divides the deaths in components_statcan.csv by the July 1 population.',
 'year,birth_rate_per_1000,total_fertility_rate'],
 [r['year'] + ',' + r['birth_rate_per_1000'] + ',' + r['total_fertility_rate'] for r in rows])

# --- social/security_statcan.csv
src = read('social/security_from_statcan.csv')
rows = [r for r in src if int(r['year']) >= FIRST]
emit('social/security_statcan.csv', [
 '# Statistics Canada 35-10-0068, police-reported homicide victims and the published rate per 100,000, curated unchanged.',
 '# Police-reported (place of occurrence, incidents) and UNODC\'s harmonised intentional homicide are different counts of an adjacent thing; two lines, both labelled, never spliced. Death-registered homicide (X85-Y09) is a third, in mortality_statcan.csv.',
 'year,homicide_count,homicide_rate_per_100k'],
 [r['year'] + ',' + r['homicide_count'] + ',' + r['homicide_rate_per_100k'] for r in rows])

# --- social/mortality_statcan.csv
src = read('social/mortality_from_statcan.csv')
cols = list(src[0])[1:]
rows = [r for r in src if int(r['year']) >= FIRST]
emit('social/mortality_statcan.csv', [
 '# Statistics Canada 13-10-0394, death registrations, all ages, both sexes, underlying cause, counts as published.',
 '# Underlying cause follows the certifying coroner; late years move as investigations close. COVID-19 counts the U07.1/U07.2/U10.9 codes only from 2020.',
 '# Counts only: the crude death rate divides by the July 1 population, and excess deaths follow the house rule (2015-2019 mean, no adjustment).',
 'year,' + ','.join(cols)],
 [r['year'] + ',' + ','.join(r[c] for c in cols) for r in rows])

# --- credit sidecars
src = read('credit/household_credit_from_statcan.csv')
rows = [r for r in src if int(r['year']) >= FIRST]
cols = list(src[0])[1:]
emit('credit/household_credit_statcan.csv', [
 '# Statistics Canada 38-10-0235 (378-0123), credit market debt of households and NPISHs to disposable income, seasonally adjusted, curated unchanged: Q4 stock, quarter mean, quarter count.',
 '# Debt to DISPOSABLE INCOME, not to GDP: it is the national line beside the BIS debt-to-GDP ratio, on a different denominator. Two lines, never one.',
 'year,' + ','.join(cols)],
 [r['year'] + ',' + ','.join(r[c] for c in cols) for r in rows])

src = read('credit/debt_service_from_statcan.csv')
rows = [r for r in src if int(r['year']) >= FIRST]
cols = list(src[0])[1:]
emit('credit/debt_service_statcan.csv', [
 '# Statistics Canada 11-10-0065, household debt service indicators, seasonally adjusted at annual rates, curated unchanged: the ratio households actually paid, plus the mortgage share.',
 '# StatCan measures payments out of the balance-sheet accounts; the BIS ratio is modelled on an assumed maturity. The two disagree by design and are never spliced.',
 'year,' + ','.join(cols)],
 [r['year'] + ',' + ','.join(r[c] for c in cols) for r in rows])

print('curated.')
