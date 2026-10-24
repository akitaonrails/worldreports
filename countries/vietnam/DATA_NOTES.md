# Vietnam — data notes

These notes cover what the sources were like to work with, and the
judgement calls a reader of the plates should not have to work out
backwards. `SOURCES.yaml` carries the caveats for each file; this file
carries the ones that span several files. The research pass and the
consolidation were both done on 2026-10-22. `DISCOVERY.md` is the
research pass's own report, kept as a record. Where it and this file
disagree, this file and `SOURCES.yaml` are right.

## Reviewed publication layer (2026-10-23)

Phase B promoted every plotted input from its fetch sidecar to a stable name
without changing a byte of its data rows. `plates.py` reads only those stable
publication copies; `provenance.json` and the country tests enforce that no
`_from_` or `_check` file can reach a published chart. Missing histories remain
visible pending panels rather than inferred values: the SBV policy rate, the
ten-year government yield, household debt, comparable excess deaths and the
four-region statutory minimum wage. Commercial lending rates remain on the
credit plate rather than being relabelled as policy rates. The
Transparency International CPI was staged on 2026-10-23 from its pinned 2025
workbook, using only the comparable 2012-method series.

---

## One national publisher, two doors, and only one door is used

Nearly every national number comes from Cục Thống kê, the National
Statistics Office (NSO; formerly the GSO, now under the Ministry of
Finance). Its PxWeb 2019 database republishes the State Bank, the MOF,
Customs, the Procuracy, the Ministry of Public Security and the Ministry
of Health. None of those bodies has a machine endpoint this machine can
reach (see `meta.pending`).

The NSO database has two doors:

- **The JSON API** serves five databases and rounds every value to the
  table's SHOWDECIMALS. Through it, the TFR is "2" in every year.
- **The HTML table pages** serve everything at full precision. They do
  it through an ASP.NET postback that returns JSON-stat v1 with a BOM
  and a trailing NUL. Errors come back as HTTP 200 on
  `/ErrorGeneral.aspx`.

`fetch_nso.py` takes **every** number through the HTML door. The API is
used only as an asserted cross-check, for V02.02 population and V02.59
unemployment. The research pass had listed five population and labour
files under API URLs. Those URLs now point at the HTML door.

The NSO labels carry status: "Sơ bộ" (preliminary) and "Ước tính"
(estimate). The fetcher parses the year off the label and keeps the
status in a `status` column. Where a file merges tables, the most
tentative status wins. The yearbook tables stop at 2025.

## The 2009/2010 GDP revaluation runs through five files

In 2019 the NSO revalued GDP upward from 2010 onward only. V03.01
carries 2000–2002 and 2009 on the old scale (2009 = 1,809,149 bn VND)
and 2010+ on the new scale (2010 = 2,739,843). 2003–2008 are absent.

| File | How the seam is handled |
|---|---|
| `macro/gdp_from_gso.csv` | every level in `_old_scale` (≤2009) and `_revalued` (≥2010) columns, plus a `gdp_scale` column |
| `macro/gdp_from_adb.csv` | `_old_scale` / `_new_scale`; it supplies 2005–2008, which the NSO table no longer has; OBS_STATUS B at 2010 is asserted |
| `international/gdp_usd_from_wb.csv` | `gdp_usd_old_scale` (2006–2009: 106.0bn in 2009) and `gdp_usd` (2010+: 147.2bn) |
| `international/gdp_usd_from_imf.csv` | **back-cast**, so continuous (2009 129.0bn, 2010 143.3bn); the only continuous US$ level, labelled as the IMF's |
| ratios (`openness_from_wb`, `private_credit_from_wb`, ADB `*_pct_gdp`, NSO V09.14) | one column; the seam is in the denominator and is named in the comments (WB private credit 2009 103.3 → 2010 90.4) |

Real growth is within-scale and continuous on every source: 2009 5.40,
2010 6.42, and NSO = ADB = WB to two decimals. **Growth across
2009→2010 computed from levels is methodology, not growth.**

## Breaks verified at consolidation

- **Gini, 2019→2020.** The national Gini falls from 0.423 to 0.375,
  with no footnote, and the 2025 value (0.323, "Sơ bộ") falls again.
  Every Gini column is split into `_2002_2019` and `_2020_on`. The World
  Bank's consumption Gini (35.7 in 2018, 36.8 in 2020) shows no such
  step, which supports reading it as a survey or method change rather
  than as redistribution.
- **Poverty standards.** V14.46 runs on an income line to 2016, the
  2016–2021 multidimensional standard for 2020–2021, and the 2022–2025
  standard from 2022. 2017–2019 are absent. The `standard` column is
  **the fetcher's inference** from the PX NOTEX and the V14.01
  comparison; the NSO does not publish it as a field. `year_label` keeps
  the published markers ("2021*", "2023**"). V14.01 puts 2016 on the new
  standard (9.2, against 5.8 in V14.46) and carries 2017–2019. So there
  are two tables and two lines, and each standard is drawn as its own
  segment. The World Bank's national headcount (SI.POV.NAHC) is a
  **population** share on a different line (2010 jump) and is kept in
  its own file. The canonical poverty slot is explicitly a share of people
  and therefore uses only SI.POV.NAHC. The NSO household-rate histories remain
  documented and available, but are not overlaid on that person-based panel.
- **Traffic deaths, 2021→2022.** Deaths go from 5,790 to 13,551 and
  accidents from 11,487 to 23,352. Minor collisions fall in 2022
  (4,055 → 3,490), rise again in 2023 (5,766) and are blank in 2024.
  Columns are split into `_to2021` / `_from2022`. Per 100,000 on the
  NSO's own population: 2019 7.9 (WHO model 23.5), 2022 13.6 (WHO
  15.1), 2023 11.9 (WHO 12.9). The police count is about a third of the
  model before the break and converges after it, so the gap is the
  finding. V14.87 is **not** a breakdown of V14.86:
  - its 2022 mode sum is 6,397, which is on the old basis;
  - its 2023–2024 mode sums match V14.86 within 3%;
  - its 2024 national row (3,855) disagrees with its own modes (11,101).
- **Life expectancy, 2021 = 2022 = 73.642039 years**, identical to six
  decimals. It is a carried value, asserted and flagged. The World Bank's
  WPP-based series moves (74.14 → 74.50).
- **Labour, 2020→2021.** ADB flags ICLS 13 → ICLS 19 (OBS_STATUS B at
  2021, in `break_flags`). Its 2010–2018 rows are re-weighted to the
  2019 census.
- **BoP, 2013→2014.** BPM5 → BPM6, flagged B in the ADB files.

## Calendar years throughout

A brief once said that Vietnam's fiscal year starts in April. It does
not. Under the Law on the State Budget, the budget year runs from
1 January to 31 December. No fetcher keys anything on an April year:
every fiscal file is keyed on the calendar year, and ADB's DF_GOV_FIN
says "Ending 31 December". Two ADB labels look like fiscal years and
are not:

- DF_LFE's REF_YEAR reads **"Ending 30 June"**. The values are the
  NSO's calendar-year labour force survey, and 2024–2025 equal the
  NSO's own figures to two decimals.
- The BoP codes `BO_BP6_FY_*` use "FY" as ADB indicator naming.
  DF_GLOB_BOP's REF_YEAR is "Calendar Year".

## Two publishers, one idea (all kept apart)

| Idea | Lines | Difference |
|---|---|---|
| Fiscal | NSO state budget (cash, central + local) · ADB general government GFSM 2014 (to 2022) · IMF WEO gross debt / net lending | 2022 net lending: ADB −3.6% of GDP, IMF **+0.7%**; NSO revenue 2020 18.8% vs ADB GG 16.2% |
| HDI | NSO's own (V14.01) · UNDP | 2023: 0.746 vs 0.766 |
| Poverty | V14.46 · V14.01 · WB NAHC · WB $3/day | 2016: 5.8 vs 9.2 |
| Unemployment | NSO working age · ADB 15+ · IMF | 2020: 2.48 / 2.25 / 2.5; 2024: 2.24 / 2.24 / 2.2 |
| Road deaths | NSO police count · WHO RS_198 model | see above |
| Homicide | UNODC via WB (2001–2011) · WHO model (2000–2021) · WHO GHE interpersonal violence (to 2023) | no national count exists |
| Population | NSO average (V02.02) · WB/WPP mid-year | 2024: 101.34mn vs 100.99mn; 2010: 87.07 vs 87.46 |
| Deaths | NSO survey CDR · registered deaths (2018–2024) · WPP · WHO GHE | 2024: 5.6 vs 6.2 (629,465 registered) vs 6.65 per 1,000; GHE 2023 720,006 deaths |
| Credit | NSO credit to the economy (2015+) · ADB claims on the private sector (2005+) · WB private credit % GDP (to 2022) | 2024: 15,619.5 tn vs 15,705.6 tn VND |
| FX | NSO central rate (2018+) · WB/IMF average · ADB end-period · Yahoo market quote | Dec 2024: market 25,476 vs central-rate average 24,170 |

## Spine departures to record when the plates are built

- **Credit.** Vietnam has no verified household-debt series, and the BIS
  total-credit dataset does not cover it. The canonical household-debt slot
  therefore remains pending. Economy-wide private credit is retained only in
  the country lens and is never presented as household debt. Credit to the
  economy is about 145% of GDP in 2025 (18,598 tn / 12,848 tn VND).
- **Mortality** has no ICD-coded death register. The NSO publishes
  three things here:
  - a survey-based CDR;
  - registered deaths from 2018 only, with a late-registration lag
    that moves the COVID peak from 2021 into 2022;
  - HIV/AIDS deaths.

  Causes come only from the WHO's modelled Global Health Estimates. For
  example, GHE puts COVID-19 deaths in 2021 at 85,608. The chapter has
  to say "modelled" in its title. The short registered-deaths history cannot
  supply the canonical 2015–2019 excess-deaths baseline, so that slot is
  pending rather than recomputed against the incomplete 2018–2019 window.
- **Security** has no national homicide count. The NSO publishes only
  what the justice system processed (V14.77): prosecutions,
  indictments and trials. A rise in those numbers measures enforcement
  as much as crime.
- **Migration** is about emigration. There is no flow statistic in
  either direction. The chapter has these pieces:
  - the UN DESA stock: 3.69 million people born in Vietnam lived abroad
    in 2024, in the United States, Japan, Australia, Taiwan, Korea and
    Canada;
  - WPP net migration;
  - secondary-income credit as a labelled remittance **superset**,
    because the World Bank's remittance series for Vietnam is empty;
  - NSO internal migration, labelled as internal.

  WPP and the World Bank both put 2006 net migration at +482,399, which
  is an artefact. The immigrant stock in Vietnam (326,418) is on a
  citizenship-plus-refugees basis, not country of birth.

## What the fetchers had to work around

- **ADB KIDB footnotes** carry a leading span that is the span of the
  **query**, not of the years the note covers. They are copied verbatim.
- **UN WPP's Data Portal API now answers 401** to every data query. The
  bulk CSV is resolved from `downloads.json`.
- **UN Comtrade** takes one period per call and throttles with 429.
  2024–2025 come back empty. They are left out (not zero) and asked for
  again on every run.
- **The IMF DataMapper** refuses a browser user agent, and its country
  path does not filter.
- **UN DESA's xlsx** serves an HTML error page to a bare client. The
  fetcher checks for the PK magic before parsing.
- **Yahoo `VND=X`** repeats the running month as a live bar. The file
  keeps 275 distinct months (2003-12 to 2026-10), and `partial=1` marks
  the current month.
- **The NSO's central rate (V03.21) is blank for 2015–2017**, even
  though the table covers 2015–2025. USD deposit rates are really 0
  from 2016, because the SBV cap is in force.
- **The NSO publishes trade partners as names only.** `partner_iso3` is
  the fetcher's mapping, and a new label fails the run. China appears
  as "CHND Trung Hoa".
- **HIV (V14.19).** The per-100,000 columns exist only for 2024, and
  the NSO's label names "2024" on the rate row. AIDS cases run to 2017,
  and cumulative deaths start in 2022.
- **V14.01's population column** is the V02.02 series except at 2014
  (90,728.9 vs 91,203.8, an older vintage) and 2022 (99,461.7 vs
  99,467.9). Every per-capita rate uses V02.02.

## Changes made at consolidation

- `fetch_nso.py`'s `write_csv` now sorts rows by year, keeping category
  order within a year. It also drops any column that the NSO table
  leaves blank in every year, and names the dropped columns in the CSV
  header. Before this change, `income_quintiles`, `internal_migration`
  and both trade-partner files had years out of order. Four revenue
  %-of-GDP heads, five spending %-of-GDP heads and the trade-balance
  growth index were empty columns. **No value changed.** The non-blank
  cells are identical before and after.
- `fetch_adb.py` writes `break_flags` only when some observation is
  flagged. As a result, `credit_from_adb.csv` and
  `gg_finance_from_adb.csv` lose the empty column, while
  `unemployment_from_adb.csv` and `remittances_proxy_from_adb.csv`
  keep it.
- The V14.01-vintage comment in `fetch_nso.py` was corrected to what
  the data show.

## Cross-source checks run in consolidation

| Chapter | Check | Result |
|---|---|---|
| Economy | real growth NSO / ADB / WB / IMF | 2024: 7.04 / 7.04 / 7.04 / 7.0; 2021: 2.55 / 2.55 / 2.55 / 2.6 |
| Economy | CPI NSO V11.08 vs IMF | 2008 +22.97 vs 23.1; 2024 +3.63 vs 3.6 |
| Economy | NSO GDP per person × population vs WB US$ GDP 2024 | within 2% (asserted); WB 476.3bn, IMF 459.4bn |
| Fiscal | NSO state budget vs ADB GG vs IMF | concepts differ by 2–3 pt of GDP; ADB vs IMF net lending agree in 2018 (−1.0) and 2020 (−2.8 / −2.9) but not 2022 (−3.6 / +0.7) |
| Trade | NSO V09.01 vs Comtrade 2023 | exports 354.72 vs 353.08bn (asserted within 0.5%); imports 326.61 vs 325.44bn |
| Trade | NSO V09.01 vs NSO/ADB BoP goods exports 2023 | identical (354,721) |
| Markets | NSO central rate vs WB average | 2020: 23,208.78 vs 23,208.37 |
| Markets | VN-Index year-end (CafeF) | 2006 751.77 · 2008 315.62 · 2024 1,266.78 · 2025 1,784.49 (asserted) |
| People | unemployment NSO vs ADB | equal in 2024–2025; NSO higher before (age base, ICLS) |
| World | HDI NSO vs UNDP 2023 | 0.746 vs 0.766 |
| World | reserves | WB only (2024 83.1bn); NSO has only the annual change |
| Demography | population NSO vs WB | within 0.5% |
| Demography | TFR NSO vs WB | 2024: 1.91 vs 1.895 |
| Security | police road deaths per 100k vs WHO | 7.9 vs 23.5 (2019); 11.9 vs 12.9 (2023) |
| Mortality | registered deaths vs WHO GHE all causes | 2021: 625,455 vs 708,741 (model) |
| Credit | NSO credit vs ADB claims on the private sector | 2024: 15,619.5 vs 15,705.6 tn VND (0.6%) |
| Migration | secondary-income credit ADB vs NSO V03.20 | equal 2018–2025 (2025: 19,766) |
