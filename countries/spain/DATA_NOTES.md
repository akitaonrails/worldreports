# Spain — data notes

What these sources were like to work with, and the judgement calls a reader
of the plates should not have to reverse-engineer. `SOURCES.yaml` carries
the per-file caveats; this file carries the ones that cross files.
Research pass: 2026-10-22.

---

## The migration chapter's seam is inside the Eurostat series itself

SOURCING_A_COUNTRY §4a warns about splicing two methodologies into one
line. Spain's case needs no splicing by us — **Eurostat's harmonised
series is already spliced at 2021**: `migr_imm1ctz` carries 467,918
immigrations for 2020 and 887,960 for 2021, and the 2021 value is exactly
the INE's EMCR figure. The INE publishes 2021 on BOTH methodologies: the
old Estadística de Migraciones says 528,856, the new Estadística de
Migraciones y Cambios de Residencia says 887,960 — a 68% jump that is
pure methodology, not movement.

So the national pair `migration/migration_flows_from_ine.csv` (EM, to
2021) and `migration/migration_flows_emcr_from_ine.csv` (EMCR, from 2021)
is staged precisely to make that seam visible, and the plate must draw
the Eurostat series with a break marker at 2021 — not let the line climb
smoothly through it. This is Spain's version of the UK's three-regime
problem, with one regime change instead of three.

## The citizenship cut and the birth cut diverge by the naturalisation rate

On 1 January 2025 Spain held 42.2mn Spanish citizens and 6.9mn foreign
citizens, but 39.7mn Spain-born and 9.5mn foreign-born residents. The
~2.5mn gap between the two "foreign" numbers is people who became
Spanish — and `migr_acq` says 252,476 did so in 2024 alone, which is why
the foreign-citizen stock can grow slowly in years of record arrivals.
The three files (stocks on both cuts, acquisitions) are staged so the
plate can show exactly that; §4a's whole discipline applies.

## Recessions: one slump or two, and what the bands claim

The bands in `country.yaml` follow the sign of quarter-on-quarter
seasonally-adjusted real GDP (Eurostat `namq_10_gdp`): negative every
quarter from 2008 Q3 to 2009 Q1, again every quarter from 2011 Q1 to
2013 Q3, and in 2020 Q1–Q2. Between them, 2010 Q1 and Q3 were negative
without two in a row, so 2010 is outside both bands. Some dating runs
the second recession 2011 Q2–2013 Q2; the band runs a quarter longer on
both sides and says so in the yaml comment. The two bands are never to be
merged into one "2008–2013 slump" band: the 2009 Q2–2010 Q4 pause was
real (six positive quarters), even if it never recovered the output lost.

COVID is banded Q1–Q2 2020 only — Spain's rebound started in Q3 — which
is tighter than Canada's whole-2020 band. The depth was worse here than
anywhere in the G20: −17.8% in Q2, because the economy leans on tourism.

## The CPI base moved again — to 2025 — while this file was being written

INE's IPC series IPC290751 is the legally linked national index, and it
is published today in **base 2025** (the base moved 2006 → 2011 → 2016 →
2021 → 2025, the last change landing in early 2026). The linked series
makes levels comparable across the window, but no level in the file is
the index anyone quoted at the time. The rate staged in
`macro/ipc_from_ine.csv` is the year-on-year change of the annual mean
index, which reproduces the official "variación media anual" (2008: 4.08
vs official 4.1; 2024: 2.77 vs 2.8). The HICP is staged beside it and is
a different animal: different basket, different coverage, and 2020 reads
−0.3 on both. Two columns, never spliced.

## Eurostat's harmonised unemployment starts in 2009 for Spain

`une_rt_a` (LFS, 15–74) simply has no ES values for 2006–2008 — the
dimension reaches back to 2003 but the cells are empty. The blanks are
carried as blanks; the INE's EPA annual average covers the whole window
(2006: 8.45) and is the primary series. Where the two overlap they agree
to the tenth (2013: 26.1 on both).

## Three interest rates that are not the policy rate

Spain's policy rate is the ECB's deposit facility rate (with the MRO
beside it, blank before October 2008 because the fixed-rate-tender series
starts there — France's file has the same blanks). Beside it:
`irt_lt_mcby_a`, the Maastricht 10-year benchmark yield (2012: 5.85% —
the euro crisis in one number), and the Banco de España's Euribor-12m and
TEDR on new housing loans, which is what households actually paid. The
TEDR compilation changed with Circular 5/2012 (2014 data onward), so the
pre/post-2014 levels are not strictly one definition.

## Household debt is a stock; doubtful loans are a stock

The Banco de España's credit series are monthly STOCKS in thousands of
euro. The first version of `fetch_bde.py` summed the months — a correct-
looking number twelve times too big (the quarterly-annualisation trap in
monthly clothing). The fetcher now reads December, and the NPL ratio
(doubtful ÷ total, computed and labelled) peaks at 13.6% in December
2013. The BdE API itself: observations arrive **newest-first** with null
holes, the units live only in the `informacion` metadata, it gzips even
when identity encoding is requested, and unknown paths answer with an
HTML 404 page under HTTP 200.

Household debt reads as % of gross disposable income (households + NPISH,
the standard Spanish pairing): 138% at the 2010 peak, 75% by 2025.

## Two debts, both correct

The fiscal layer is entirely the EDP/Maastricht transmission
(gov_10dd_edpt1, gov_10q_ggdebt): general government, consolidated. 2024
reads 101.4% of GDP — down from 105.3% in 2023 partly because the
denominator was revised up (2024 GDP now €1,598.6bn, a benchmark
revision that also lifted 2024 growth to 3.7%). The Tesoro's "deuda del
Estado" is the STATE only, a materially smaller number, and is routinely
quoted as "Spain's debt"; it is not staged (its site was unreachable this
session) and if added later it goes BESIDE the EDP series, never into it.

## Vital statistics: the last year is missing on purpose

MNP definitive births and deaths run to 2024; 2025 exists only as the
provisional monthly estimates (EMN/EDeS), a different vintage that revises
upward as late registrations arrive. 2025 is blank in
`social/vital_from_ine.csv` rather than provisional — the provisional
series belongs beside it, not in it. ECM (causes of death, by death
certificate) also ends 2024 and lags by about 18 months. Its "Agresiones
(homicidio)" row (324 deaths in 2024) is the death-certificate homicide
count that pairs with the police count the Interior portal could not
serve this session; the two count different populations and disagree in
both directions.

## EPA's 2021 vintage seam

The EPA was reweighted to the 2021 census and its questionnaire
modernised in 2021; INE back-computed the headline rates, so the staged
series is continuous, but a plate that makes too much of a 2021 step in
any EPA breakdown should check the vintage note first.

## What is not here yet

Crime (Interior portal walled — see HANDOFF), IGAE/Tesoro national fiscal
series (unreachable this session; the EDP fallback is in use and is the
same aggregate Spain transmits), merchandise trade by partner and product
(DataComex, not probed), and Transparency International's CPI (curated by
hand with the 2012 break, as France does). All four are in the pending
block of `SOURCES.yaml` or the HANDOFF.
