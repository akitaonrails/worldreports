# Credit availability, interest rates and household indebtedness — France

Research note for `data/credit/`. Retrieved **2026-10-21**. All endpoints below were called over plain
HTTP with a browser User-Agent; raw responses are cached under `cache/credit/` (PDFs under
`cache/credit/pdf/`).

Files written:

| file | coverage | primary institution |
|---|---|---|
| `lending_rates.csv` | 2006–2026 (2026 = Jan–Aug) | ECB / Banque de France (MIR) |
| `household_debt.csv` | 2006–2026 (2026 partial) | ECB QSA, Eurostat, BIS |
| `credit_outstanding.csv` | 2006–2026 (2026 = Aug) | ECB / Banque de France (BSI) |
| `overindebtedness.csv` | 2007–2026 (2026 = Jan–Sep) | Banque de France |
| `credit_holding_ocm.csv` | 2006–2025 | OCM (FBF + ASF) — **industry survey, not official** |

---

## 1. `lending_rates.csv`

**Institution.** European Central Bank Data Portal, dataflow `MIR` (MFI Interest Rate statistics).
France's data are collected and reported by the Banque de France (`SOURCE_AGENCY = FR2`). No API key
needed.

**Endpoint.**
`https://data-api.ecb.europa.eu/service/data/MIR/<key>?format=csvdata&startPeriod=2006-01`

Key order is `FREQ.REF_AREA.BS_REP_SECTOR.BS_ITEM.MATURITY_NOT_IRATE.DATA_TYPE_MIR.AMOUNT_CAT.BS_COUNT_SECTOR.CURRENCY_TRANS.IR_BUS_COV`.
The full list of 227 French `MIR` keys is cached at `cache/credit/mir_fr_keys.csv`, obtained with
`.../MIR/M.FR.B.......?detail=serieskeysonly`.

| column | series key | definition |
|---|---|---|
| `housing_new_total_pct` | `M.FR.B.A2C.A.R.A.2250.EUR.N` | new loans for house purchase, all initial rate-fixation periods |
| `housing_new_fix_over10y_pct` | `M.FR.B.A2C.P.R.A.2250.EUR.N` | new housing loans, rate fixed > 10 years |
| `housing_new_fix_1to5y_pct` | `M.FR.B.A2C.I.R.A.2250.EUR.N` | new housing loans, fixation > 1 and ≤ 5 years |
| `housing_new_var_upto1y_pct` | `M.FR.B.A2C.F.R.A.2250.EUR.N` | new housing loans, floating / fixation ≤ 1 year |
| `consumer_new_total_pct` | `M.FR.B.A2B.A.R.A.2250.EUR.N` | new loans for consumption, excluding revolving/overdraft/card |
| `revolving_overdraft_hh_pct` | `M.FR.B.A2Z.A.R.A.2250.EUR.N` | revolving credit, overdrafts, convenience + extended card credit |
| `other_lending_hh_new_pct` | `M.FR.B.A2D.A.R.A.2250.EUR.N` | new "other lending" to households |
| `nfc_new_total_pct` | `M.FR.B.A2A.A.R.A.2240.EUR.N` | new loans to non-financial corporations (S.11), all amounts |
| `housing_outstanding_stock_pct` | `M.FR.B.A22.A.R.A.2250.EUR.O` | rate carried by the **outstanding stock** of housing loans |
| `cons_other_outstanding_stock_pct` | `M.FR.B.A25.A.R.A.2250.EUR.O` | rate carried by the outstanding stock of consumer + other lending |

**Unit / rate concept.** Percent per annum, *Annualised Agreed Rate / Narrowly Defined Effective Rate*
(AAR/NDER), euro-denominated contracts, counterpart = households and NPISH (S.14+S.15).

**Vintage.** ECB `MIR` monthly, available 2003-01 → **2026-08** at retrieval. Observation status `A`
(normal) throughout the French series.

**Caveats that change the reading.**

- **NDER ≠ TAEG ≠ taux d'usure.** NDER excludes ancillary charges (arrangement fees, compulsory
  borrower insurance, guarantee fees). The French statutory *TAEG* includes them, and the *taux
  d'usure* ceiling published quarterly (monthly from Feb 2023 to end-2023) by the Banque de France is
  set against TAEG. So an NDER of 4.0% is *not* comparable to a usury ceiling of ~6%, and a chart
  mixing the two is wrong. There is no usury-rate series in `MIR`; it is published as a table in the
  *Journal officiel* / on the Banque de France site and is **not included in these files**.
- **New business includes renegotiations.** `A2C.A` covers renegotiated contracts. In 2016–2017 and
  again in 2020–2021 renegotiation waves pulled the French average down; ACPR reports renegotiations
  at 16–17% of annual housing-loan production in 2023–2024 (see §6).
- **The new-rate / stock-rate gap is the story, and it is structural.** Annual averages from this file:
  housing new business 1.15% (2021) → 3.01% (2023) → 3.39% (2024) → 3.02% (2025) → 3.12% (2026, Jan–Aug);
  the *stock* rate only moved 1.56% (2021) → 1.47% (2022, still falling) → 1.99% (2026). The stock rate
  was still *falling* in 2022 while new rates had already turned up.
- **Why: French mortgages are overwhelmingly fixed-rate for the whole life of the loan — verified, not
  assumed.** ACPR, *Le financement de l'habitat en 2024* (Analyses et Synthèses n°174, July 2025),
  "Chiffres clés": fixed rate = **98.1% of the outstanding stock in 2023 and 98.5% in 2024**; the text
  states housing loans are granted "à taux fixe (99 % de la production)". Section 7 is titled "Une
  production et des encours quasi totalement à taux fixe". Source PDF
  `https://acpr.banque-france.fr/system/files/2025-07/20250730_AS174_Financement_habitat_2024.pdf`
  (acpr.banque-france.fr was unreachable on 2026-10-21 — see §7 — so read from
  `https://web.archive.org/web/20251002235053if_/<that URL>`, cached as
  `cache/credit/pdf/acpr_habitat_2024.pdf`).
  Consequence: ECB policy-rate pass-through to the *existing* French household loan book is slow and
  partial. It reaches new borrowers quickly and existing borrowers barely at all. The
  `housing_new_var_upto1y_pct` column in this file is the floating-rate segment and is a very small,
  atypically priced slice — do not use it as a proxy for the market.
- **Annual averages are computed here, not published.** Each `_pct` column is the unweighted arithmetic
  mean of that year's monthly observations (the ECB publishes no annual average, and a
  volume-weighted average is not possible: `MIR` has no per-fixation-bucket volume series for France,
  only `M.FR.B.A2C.A.B.A.2250.EUR.N` for the total). `months_covered` states how many months entered
  each row. **2026 = 8 months, January–August 2026, partial.**
- `housing_new_total_dec_pct` gives the December observation alone, for anyone who prefers an
  end-of-year reading. It is blank for 2026.
- `other_lending_hh_new_pct` is blank for 2018 — the ECB publishes no value for that year's months in
  `A2D.A`; not an extraction error.

---

## 2. `household_debt.csv`

Four different official measures sit side by side. **They must not be spliced.** They differ in
consolidation, instrument scope, denominator and vintage.

### (a) ECB Quarterly Sector Accounts — the debt-to-income measure

`https://data-api.ecb.europa.eu/service/data/QSA/<key>?format=csvdata&startPeriod=2005-Q1`

- `hh_debt_pct_gdi_ecb_nco_q4`, `_qavg` — key
  `Q.N.FR.W0.S1M.S1.N.L.LE.F4.T._Z.XDC_R_B6GA_CY._T.S.V.N._T`
  Loans (F4) owed by households+NPISH (S1M), **non-consolidated**, as % of the four-quarter moving sum
  of **adjusted** gross disposable income (B6G adjusted for the change in net equity of households in
  pension fund reserves). This is the *taux d'endettement des ménages* concept the Banque de France
  communicates. ECB series title: "Loans granted to households, ratio of adjusted gross disposable
  income".
- `hh_debt_pct_gdp_ecb_nco_q4` — same but `XDC_R_B1GQ_CY` (% of GDP).
- `hh_debt_eur_mn_ecb_nco_q4` — same but `XDC` (level, EUR million).
- **Only the non-consolidated variant exists for France in QSA.** The consolidated keys
  (`...S1M.S1.C.L.LE.F4...`) return no data.
- Vintage: `hh_debt_pct_gdi...` runs to 2026-Q1; the GDP ratio and the level run to 2026-Q2.

### (b) Eurostat annual financial balance sheets — consolidated vs non-consolidated

`https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nasa_10_f_bs?geo=FR&format=JSON&lang=en&sector=S14_S15&na_item=F4&finpos=LIAB&unit=PC_GDP&unit=MIO_EUR&co_nco=CO&co_nco=NCO`

ESA 2010, end-of-year stocks, 1995–2025. Dataset extraction timestamp reported by Eurostat:
`2026-10-21T23:00+0200`.

- `hh_debt_pct_gdp_eurostat_nco` — **non-consolidated** loans, % of GDP.
- `hh_debt_pct_gdp_eurostat_co` — **consolidated** loans, % of GDP.
- `hh_debt_eur_mn_eurostat_co` — consolidated level, EUR million.
- For French households CO and NCO are **almost identical** (households barely lend to each other):
  2024 gives 1,767,588 M€ consolidated vs 1,767,599 M€ non-consolidated, both 60.2% of GDP. The two
  columns are kept separate anyway, because the distinction is material for other sectors and because
  a reader comparing France to a country where the gap is large must know which one they have.
- **`tipsd21` is dead.** The old Eurostat "private sector debt" indicator returns
  `ERR_NOT_FOUND_4: TIPSD21 (DATA_FLOW:ALL,1.0) is not available for dissemination` (404) as of
  2026-10-21. Do not cite it.
- **Eurostat's own GDI unit is empty for France.** `nasa_10_f_bs` advertises a `PC_GADI` unit
  (% of gross adjusted disposable income) and it is listed in the dimension metadata, but
  `unit=PC_GADI` for FR / S14_S15 / F4 / LIAB returns `"value":{}` — no observations. That is why the
  debt-to-income column in this file comes from ECB QSA and not from Eurostat.
- The Eurostat SDMX 2.1 and 3.0 endpoints both refused `format=csvdata`
  (`UNSUPPORTED_FORMAT`); the `statistics/1.0` JSON-stat endpoint is the one that works.

### (c) BIS Total Credit

`https://stats.bis.org/api/v2/data/dataflow/BIS/WS_TC/2.0/Q.FR.H.A.M.770.A?format=csv` (% of GDP)
`https://stats.bis.org/api/v2/data/dataflow/BIS/WS_TC/2.0/Q.FR.H.A.M.XDC.A?format=csv` (EUR bn)

Key order `FREQ.BORROWERS_CTY.TC_BORROWERS.TC_LENDERS.VALUATION.UNIT_TYPE.TC_ADJUST`; here
borrower = Households & NPISHs, lender = **all sectors**, market valuation, **adjusted for breaks**.
Note the dataflow is **version 2.0** — `WS_TC/1.0` returns "No structures match query parameters".

- BIS credit is a wider instrument scope than ESA `F4` loans (it includes debt securities issued by the
  sector), and the break adjustment makes its history a separate vintage. For households the levels
  land very close to (a) and (b), which is a useful cross-check — but they are still not the same
  series.

### (d) BIS Debt Service Ratio — the most policy-relevant column

`https://stats.bis.org/api/v2/data/dataflow/BIS/WS_DSR/1.0/Q.FR.H?format=csv` (dataflow version **1.0**)

- `hh_debt_service_ratio_pct_bis_qavg` — interest plus amortisation on household debt as a share of
  household income, mean of that year's available quarters. France sits around **6%** and barely moved
  through the 2022–2024 rate rise (6.6% in 2022 → 6.0% in 2024–2026). That flatness is the fixed-rate
  mortgage structure showing up in household cash flow. BIS warns the DSR is an *estimate* built on an
  assumed average remaining maturity and an aggregate lending rate.

### What a naive reader gets wrong here

The debt/GDP and debt/GDI ratios **fell** in 2023–2025 (GDI ratio 102.2% in 2021 → 90.8% in 2024)
*while interest rates rose*. That is not households paying debt down: the euro level of household debt
was essentially flat (1,747.8bn end-2022 → 1,767.6bn end-2024), and nominal income and nominal GDP grew
fast under inflation while new credit flow nearly stopped. Read this file alongside
`credit_outstanding.csv`, where the growth rates fall to ~0 and housing-loan growth goes negative, and
alongside `overindebtedness.csv`, where filings rise 2023–2025. Falling leverage ratios and rising
over-indebtedness are happening at the same time and are not in contradiction.

`quarters_covered` is the maximum number of quarters available across the quarterly columns that year.
**2026 is partial**; its `_q4` cells are blank and its `_qavg` cells are partial-year means.

---

## 3. `credit_outstanding.csv`

**Institution.** ECB Data Portal, dataflow `BSI` (MFI Balance Sheet Items); France reported by the
Banque de France.

**Endpoint.** `https://data-api.ecb.europa.eu/service/data/BSI/<key>?format=csvdata&startPeriod=2005-01`
Key order `FREQ.REF_AREA.ADJUSTMENT.BS_REP_SECTOR.BS_ITEM.MATURITY_ORIG.DATA_TYPE.COUNT_AREA.BS_COUNT_SECTOR.CURRENCY_TRANS.BS_SUFFIX`;
all keys here are `M.FR.N.A.<item>.A.<datatype>.U6.2250.Z01.<suffix>` — domestic (U6) households and
NPISH (2250), all currencies (Z01), lender = MFIs excluding the central bank. Available keys cached in
`cache/credit/bsi_keys.csv`.

**Levels** (EUR bn in the CSV; the API returns EUR million, divided by 1000 here):

| column | item | first obs |
|---|---|---|
| `hh_loans_total_eur_bn` | `A20`, unadjusted stock, all loans to households | 2003-01 |
| `hh_loans_housing_eur_bn` | `A22`, unadjusted, lending for house purchase | 2003-01 |
| `hh_loans_cons_other_eur_bn` | `A25`, unadjusted, consumption **+ other lending** | 1997-09 |
| `hh_loans_total_adj_eur_bn` | `A20T`, adjusted, total | 2003-01 |
| `hh_loans_housing_adj_eur_bn` | `A22T`, adjusted, housing | **2014-12** |
| `hh_loans_consumption_adj_eur_bn` | `A21T`, adjusted, consumption only | **2014-12** |
| `hh_loans_other_adj_eur_bn` | `A23T`, adjusted, other lending | **2014-12** |

- **"Adjusted" (`...T`) means adjusted for loan sales and securitisation** — it adds back loans moved
  off balance sheet. In France the gap is large: 2026-08 gives **1,749.8bn adjusted vs 1,564.9bn
  unadjusted**, because French banks securitise heavily into internal vehicles. The unadjusted series
  *understates* household borrowing, and drops in it can be pure securitisation events rather than
  repayment — visible in this file at 2014 (unadjusted total falls 1,112.3 → 1,091.8bn while the
  adjusted total rises 1,156.6 → 1,178.4bn, and unadjusted housing growth prints −2.8%).
  **Prefer the adjusted columns where they exist.** That is why the clean housing / consumption /
  other split only starts in December 2014.
- **There is no unadjusted consumer-credit-only item for France in `BSI`.** `A25` bundles consumption
  with other lending. A consumer-credit-only split before Dec 2014 does not exist in this dataflow.

**Growth rates.** These are the ECB's **own published** annual growth rates of the *index of notional
stocks* (`DATA_TYPE = I`, `BS_SUFFIX = A`), **not** computed from the levels above. Notional-stock
growth strips out reclassifications, revaluations, exchange-rate effects and — for the `...T` items —
securitisation.

- `growth_total_adj_pct` — `M.FR.N.A.A20T.A.I.U6.2250.Z01.A` (from 2004-01)
- `growth_housing_pct` — `M.FR.N.A.A22.A.I.U6.2250.Z01.A`
- `growth_housing_adj_pct` — `M.FR.N.A.A22T.A.I.U6.2250.Z01.A` (from **2015-12**)
- `growth_consumption_adj_pct` — `M.FR.N.A.A21T.A.I.U6.2250.Z01.A` (from **2015-12**)

**Reference month.** All columns take the **December** observation. `reference_month` records the
actual month used. **2026 shows `2026-08`** — the latest month published, not a year-end figure. Do not
treat the 2026 row as a year-end stock or compare its growth rate to a December reading without saying
so.

Headline: adjusted total household loans 804.5bn (Dec 2006) → 1,749.8bn (Aug 2026). Adjusted total
growth fell from 11.5% (2006) to **0.3% in 2024**, the weakest in the series, with adjusted housing
growth **−0.7%** in 2024; consumption credit kept growing (+4.5% in 2024, +4.0% in 2025).

---

## 4. `overindebtedness.csv`

This is the clearest "population in debt because of borrowing" indicator: filing a *dossier* with a
*commission départementale de surendettement* is the statutory entry point to the French personal
over-indebtedness procedure.

**Two separate columns from two retrieval routes, deliberately not merged.**

### `dossiers_deposes_published` — the figure the Banque de France printed

Scope: **France métropolitaine** (called *France hexagonale* from the 2025 edition).

| years | document | where the number sits |
|---|---|---|
| 2007–2011 | *Baromètre du surendettement — 4ᵉ trimestre 2011, données* | table "Données d'activité au cours des cinq dernières années", row "Dossiers déposés" |
| 2011–2015 | *Enquête typologique sur le surendettement des ménages*, editions 2011–2015 | "En \<year\>, N dossiers déposés en France métropolitaine" |
| 2016 | *Enquête typologique 2016* | "Le nombre de dossiers de surendettement déposés s'élève en 2016 à 194 194" |
| 2017 | *2017 in figures — Ten key figures on household over-indebtedness in France* | "181,123 situations of over-indebtedness were submitted to the household debt commission secretariats" |
| 2018 | *2018 in figures* | "out of a total of 162,936 cases of overindebtedness recorded in 2018" |
| 2022–2025 | *Enquête typologique* 2022/2023/2024, *Typologie du surendettement des ménages* 2025 | annex "POPULATIONS STATISTIQUES ÉTUDIÉES", row "Nombre de dépôts de dossiers" |

Original URLs (all read from Internet Archive captures — see §7):

- `http://www.banque-france.fr/fileadmin/user_upload/banque_de_france/La_Banque_de_France/barometre-surendettement-2011T4_donnees.pdf`
  via `https://web.archive.org/web/20120530005306if_/<URL>`
- `https://particuliers.banque-france.fr/sites/default/files/media/2016/10/13/enquete-typologique-surendettement_<2010|2011|2012|2013|2014|2015>.pdf`
- `https://particuliers.banque-france.fr/sites/default/files/media/2017/02/28/enquete-typologique-2016-sur-le-surendettement_2017-02-28.pdf`
- `https://particuliers.banque-france.fr/sites/default/files/media/2018/03/09/suren-2017_reperes_en_v3.pdf`
- `https://particuliers.banque-france.fr/sites/default/files/media/2019/02/15/suren-2018_key-figures.pdf`
  (the four above via `https://web.archive.org/web/20220320123532if_/<URL>`; the index page they come
  from is `https://particuliers.banque-france.fr/en/node/1268`, "Études sur le surendettement")
- `https://www.banque-france.fr/system/files/2023-02/suren-2022_enquete-typologique.pdf`
- `https://www.banque-france.fr/system/files/2024-02/Surendettement_Enquete-typologique_2023.pdf`
- `https://www.banque-france.fr/system/files/2025-02/Surendettement_Enquete-typologique_2024.pdf`
- `https://www.banque-france.fr/system/files/2026-04/Typologie-surendettement-2025.pdf`

Values: 2007 182,855 · 2008 188,485 · 2009 216,396 · 2010 218,102 · 2011 232,493 · 2012 220,836 ·
2013 223,012 · 2014 230,964 · 2015 217,302 · 2016 194,194 · 2017 181,123 · 2018 162,936 ·
2022 113,081 · 2023 121,617 · 2024 134,803 · 2025 148,013. 2011 agrees between the baromètre and the
2011 enquête, which is a useful internal consistency check across the two document families.

**Blank years, and why:**

- **2006 — not found.** The 2011 baromètre's five-year table starts at 2007. The 2010 and earlier
  *enquêtes typologiques* are built on *dossiers déclarés recevables* over a **partial** year (the 2010
  edition: 176,731 dossiers recevables, 1 Jan – 31 Oct 2010), which is a different statistic and is not
  entered. Press and parliamentary sources quote 184,866 for 2006 and the Banque de France's own 2007
  commentary gives "−1.1% vs 2006", but neither is a Banque de France figure for *dossiers déposés en
  2006* that I could read, so 2006 is **left blank**. Do not back it out of the −1.1%.
- **2019–2021 — no printed-edition figure captured.** Use the webstat column; it is the same
  institution and the same statistic.

### `dossiers_deposes_webstat` — machine-readable, 2019 onward

Sum of the 12 monthly observations of Banque de France series **`IFI.M.FR.SUREN.DEPOT`**, "Dépôts de
dossiers de surendettement auprès des commissions départementales de surendettement", from the Banque
de France Webstat open-data portal (an Opendatasoft instance, reachable without a key):

- base export: `https://webstat.banque-france.fr/export/csv/fr/catalogue/ifi` (semicolon-separated, ~26,500 rows)
- catalogue API: `https://webstat.banque-france.fr/api/explore/v2.1/catalog/datasets?where=search("surendettement")`
- the departmental datasets are `ifi-m-d<NN>-suren-depot`; the national aggregate carries `REF_AREA = FR`

**The monthly series starts 2019-01.** There is no earlier month anywhere in Webstat — the IFI base is
the post-2019 inclusion-financière collection. Last month **2026-09**, series `updated_at`
**2026-10-13**. Annual sums are computed here; the Banque de France publishes no annual total in this
base. The IFI base carries only the 95 metropolitan départements plus the `FR` aggregate — **no DROM**.

**Small, consistent discrepancy.** Webstat sums run a few units above the printed figures for the same
year: 2022 113,082 vs 113,081; 2023 121,621 vs 121,617; 2024 134,807 vs 134,803; 2025 148,020 vs
148,013. The gap is ≤7 cases (≈0.005%) and is almost certainly later revision of the monthly data. The
**printed** number is the citable one; the webstat column is there for 2019–2021 and 2026 and for
month-level work.

**`months_covered` applies to `dossiers_deposes_webstat`.** **2026 is PARTIAL: January–September 2026,
121,571 filings over 9 months.** It is not a year total and must not be put on a chart next to full
years without being flagged.

### Debt per dossier — 2022–2025 only, and there is a trap

From the row "Endettement global" of the debt-structure annex of the 2022–2025 editions:

| year | `endettement_global_eur_th` | `dossiers_traites` | `endettement_median_eur` |
|---|---|---|---|
| 2022 | 4,255,112 | 102,884 | 18,024 |
| 2023 | 4,205,846 | 101,960 | 18,446 |
| 2024 | 4,468,618 | 109,694 | 18,807 |
| 2025 | 4,964,717 | 120,473 | 19,278 |

- `endettement_global_eur_th` is in **thousands of euros** (so 2025 = 4.96 bn€, matching the edition's
  headline "5,0 Md€").
- `dossiers_traites` is the population the debt figures are measured on: dossiers *entièrement traités*
  during the year, excluding those whose debts duplicate another dossier. **It is not
  `dossiers_deposes`** — do not divide one by the other.
- **Break, and the reason the series stops at 2022.** From the 2022 edition the Banque de France moved
  the statistical population from dossiers *déclarés ou jugés recevables* to dossiers *entièrement
  traités*. The 2022 edition states this explicitly. Pre-2022 editions are therefore on a different
  base, and they headline a **mean** ("endettement global moyen", e.g. 42,334 € in 2016), not a median.
  Nothing before 2022 is spliced in.
- **Headline-vs-annex trap.** The 2024 edition's cover highlights **17,447 € "endettement médian hors
  immobilier"**, while its annex median *including* housing debt is **18,807 €**. The 2025 edition
  prints both (19,278 € all debt; 17,951 € excluding housing). This file uses the annex, all-debt
  figure for every year. Anyone quoting "median debt of an over-indebted French household" needs to say
  which of the two they mean.

### Context columns

- `inscriptions_ficp_personnes` — sum of 12 monthly values of `IFI.M.FR.FICP.INS_FICP`, persons newly
  registered in the FICP (national register of household credit-repayment incidents). A **flow of
  registrations** that includes ordinary payment incidents, not only over-indebtedness measures. It is
  **not** a count of over-indebted people. For the stock, the 2025 edition reports 476,000 persons
  registered in FICP under a surendettement measure at end-2025, −0.7% on the year and −45% over ten
  years; that stock is not in this file.
- `inscriptions_fcc_personnes` — `IFI.M.FR.FCC.INS_FCC`, persons registered in the *Fichier Central des
  Chèques* (bounced cheques, withdrawn payment cards). Context only; it is not credit. **2026 covers 8
  months for FCC, one month fewer than DEPOT**, and `months_covered` refers to DEPOT.

### Shape of the series

Filings ran above 215,000 a year through 2009–2015, peaked at 232,493 (2011), then fell steeply after
the 2010 Lagarde law and the 2014 and 2016 procedural reforms, bottoming at 108,748 in the Covid year
2020. They have risen every year since 2022 — 113,081 → 121,617 → 134,803 → 148,013 — but 2025 is still
**32% below 2015** (the 2025 edition's own comparison). The post-2018 fall is driven as much by
procedural change and by the collapse in *primodépôts* as by household balance sheets, so the long
series is **not** a clean indicator of financial distress over 2006–2026. Say that whenever the drop
from 232k to 109k is shown.

---

## 5. `credit_holding_ocm.csv` — optional series, weaker provenance

**Not an official statistic.** The *Observatoire des Crédits aux Ménages* is run jointly by the
**Fédération Bancaire Française** and the **Association Française des Sociétés Financières** — an
industry survey, not Insee and not Banque de France, with no official-statistics label.

- 38th edition, survey fielded **November 2025**, presented **5 March 2026**.
- `https://asf-france.com/wp-content/uploads/2026/03/OCM-Tableau-de-bord-mars-2026.pdf`
- press release: `https://asf-france.com/wp-content/uploads/2026/03/CP-FBF-38eme-edition-de-lOCM.pdf`
- Method: postal survey of a quota sample (response rate 73.1% in 2025, 9,498 usable responses in
  time), reweighted to the 2019 Insee census structure (region, agglomeration size, age and occupation
  of the head of household). Survey-based: sampling error, plus self-reporting bias about one's own
  debts. Series runs from 1989.

| column | unit | coverage |
|---|---|---|
| `share_any_credit_pct` | % of households | 1989–2025 (file starts 2006) |
| `share_housing_credit_pct` | % of households | 2010–2025 |
| `share_consumer_credit_pct` | % of households | 2012–2025 |

The two sub-shares do not sum to the total: 1.99 million households held both in 2025.

**How the numbers were obtained — read this before citing.** The OCM *tableau de bord* publishes these
as printed **data labels on charts**, with no data table anywhere in the document. The values were
extracted from the PDF **text layer** and assigned to years by horizontal position
(`pdftotext -bbox-layout`), not read off pixels. Every value the OCM also states in prose or in the
press release matches: any-credit 40.4% (2025) and 41.9% (2024); housing 28.7% (2025) and 29.7% (2024);
consumer 18.1% (2025), 19.0% (2024), 24.9% (2020). For **2010 and 2011 the housing and consumer curves
cross**, so the two labels could not be attributed to a series unambiguously and consumer credit is
left blank for those two years rather than guessed.

Headline: the share of French households holding any credit has fallen for seven straight years, from
47.8% (2017–2018) to **40.4% in 2025** — the lowest since the Observatoire began in 1989. Consumer
credit holding fell for eight straight years to **18.1%**, also a series low. This is the household-side
mirror of the near-zero credit growth in `credit_outstanding.csv`.

---

## 6. Cross-series reading guide

Four things move in directions a reader will find contradictory, and all four are real:

1. **New lending rates tripled** (1.15% → 3.4% on new housing loans, 2021→2024) while **the rate on the
   existing stock barely moved** (1.56% → 1.74%). Fixed-rate mortgages at 98.5% of the stock (ACPR).
2. **Credit growth collapsed** to +0.3% (2024) with housing loans outright shrinking, and the **share of
   households holding credit** fell to a 36-year low — the quantity channel, not the price channel, is
   where the tightening landed.
3. **Debt ratios fell** (debt/GDI 102% → 91%) because nominal income grew and new credit stopped, not
   because households repaid. The euro level of debt is flat, not falling.
4. **Over-indebtedness filings rose 36%** from 2022 to 2025 even as aggregate leverage fell. Different
   population: the filings are concentrated in low-income households whose problem is consumer credit
   and arrears on current charges, not mortgages.

Do not build a single "credit stress" index out of these.

## 7. Access problems encountered on 2026-10-21

- **`banque-france.fr`, `particuliers.banque-france.fr`, `publications.banque-france.fr` and
  `acpr.banque-france.fr` were entirely unreachable**: every path 302-redirected to
  `/maintenance/maintenance.html` ("Une opération de maintenance entraîne l'indisponibilité de ce site
  internet pour 24 heures"), regardless of User-Agent or headers. Every Banque de France and ACPR PDF
  cited above was therefore read from an **Internet Archive capture**, with both the original URL and
  the `web.archive.org/.../<timestamp>if_/` URL recorded. Re-verify against the live site once
  maintenance ends.
- **`webstat.banque-france.fr` stayed up** throughout — it is a separate Opendatasoft host and was the
  only live Banque de France source available.
- The Internet Archive **CDX API times out (504)** on domain-wide wildcard queries combined with a
  regex `filter=`. Exact-URL CDX queries are fast and were used instead. One capture of
  `suren-2022_enquete-typologique.pdf` (timestamp 20240225213834) is **truncated at exactly 1,048,576
  bytes** and unreadable by `pdftotext`; the 20240120005439 capture is complete. Always check
  `length` in the CDX listing before downloading.
- **Eurostat `tipsd21` is withdrawn** (404). Eurostat SDMX 2.1/3.0 reject `format=csvdata`; use the
  `statistics/1.0` JSON-stat endpoint.
- **BIS dataflow versions matter**: `WS_TC` is **2.0** (1.0 returns "No structures match query
  parameters"), `WS_DSR` is **1.0**. `availableconstraint` is not supported by the BIS v2 API, so valid
  key combinations have to be discovered with a wildcard `lastNObservations=1` query.
- **ECB wildcard queries that are too broad return an HTML error page**, not CSV — e.g.
  `BSI/M.FR.N.A.A2...1.U6.2250.Z01.E`. Use `detail=serieskeysonly` to enumerate first.

## 8. Things looked for and not found

- **Household debt as % of GDI from Eurostat** — the `PC_GADI` unit exists in the `nasa_10_f_bs`
  metadata but has no observations for France. Used ECB QSA instead.
- **Consolidated household debt-to-income** — does not exist for France in ECB QSA; only
  non-consolidated.
- **A consumer-credit-only outstanding stock before Dec 2014** — not in ECB `BSI` for France (`A25`
  bundles consumption with other lending; `A21T` starts 2014-12).
- **Volumes of new housing loans by rate-fixation bucket** — not published for France in ECB `MIR`
  (only the total, `M.FR.B.A2C.A.B.A.2250.EUR.N`), so a volume-weighted average new-business rate and a
  fixed-rate share cannot be computed from `MIR`. The ACPR annual report is the source for the
  fixed-rate share.
- **`dossiers déposés` for 2006** — no Banque de France figure located (see §4).
- **A long machine-readable surendettement series** — none exists. Webstat's `IFI.M.FR.SUREN.DEPOT`
  starts 2019-01; everything earlier lives only inside annual PDF editions.
- **Median debt per dossier before 2022** — definitional break (recevables → entièrement traités) plus
  a mean/median switch; not reconstructible on a consistent basis.
- **The usury rate (`taux d'usure`) series** — not in any SDMX dataflow reached; published as JO tables
  on the Banque de France site, which was down. Not included.
