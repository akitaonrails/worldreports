# Notes on the sources

Working notes from compiling this repository: what the French official
statistical system is good at, where it is hard to reach, and the specific
places where a number means something other than what its label says. These
are observations about the *sources*, not about France. Where they are
opinions, they are marked as such.

`SOURCES.yaml` records the provenance of each series and the sources table
on the page renders it. This file is the part that does not fit in a per-series note: the
patterns, and the judgement calls I had to make.

---

## 1. The short version

France publishes an unusually complete and unusually well-documented
statistical record, and makes it unusually awkward to collect
programmatically. Almost everything exists; almost nothing is one API call
away. The friction is not secrecy, it is organisation — a dozen institutions
each publishing in their own format, with the harmonised copy living at
Eurostat rather than at home.

Two institutions deserve singling out in opposite directions. The ECB's Data
Portal carries French bank interest rates, credit stocks and sector accounts
on one open, keyless, well-documented API — it is the easiest serious data in
this repository to collect. The Banque de France's own publication estate
spent a day returning a maintenance page, and the series that only exists in
its PDFs had to be read from the Internet Archive.

The hazard in French data is not missing numbers and not revisions. It is
**definitional**: the same quantity is published on two or three legitimate
definitions that differ by more than any plausible measurement error, and the
difference is documented but not advertised. Getting France wrong is
overwhelmingly a matter of picking the wrong definition and never knowing.

---

## 2. Availability, source by source

| Source | Access | Key? | Format | Verdict |
|---|---|---|---|---|
| Eurostat dissemination API | REST, open | no | JSON-stat | The best thing here. Everything national-accounts-shaped, harmonised, long series, stable identifiers. |
| ECB Data Portal (SDMX) | REST, open | no | CSV/SDMX | Excellent. Daily series back to 1999, unambiguous series keys. |
| INSEE BDM (SDMX) | REST, open | no | SDMX-ML | Works, per series, if you already know the `idbank`. Finding the idbank is the hard part. |
| INSEE melodi | REST | no | — | Returned HTTP 400 on every shape I tried. Not usable for this. |
| INSEE web downloads | xlsx/csv per page | no | spreadsheet | Reliable, not automatable without hardcoding a file URL per dataset. |
| data.gouv.fr | REST + files | no | mixed | Good catalogue. The trap is abandoned datasets (see §5). |
| DGDDI (customs) | web + open data | no | xlsx/csv | Two incompatible publications of "the same" trade data (see §4). |
| SSMSI / Interstats | web + data.gouv | no | xlsx/csv | Strong methodology notes. Comparable series starts 2016. |
| Inserm-CépiDc via DREES | REST (Opendatasoft) | no | csv | Works well. ~18-month publication lag. |
| Santé publique France | data.gouv + BEH | no | csv/HTML | Surveillance ended mid-series in 2023 (see §6). |
| Banque de France (Webstat) | REST | yes for some | csv | Mostly reachable; the ECB carries the same series without a key. Webstat stayed up while the rest of the site did not (see §14). |
| ECB MIR / BSI / QSA | REST, open | no | CSV/SDMX | The same excellent API as the rest of the ECB. French bank interest rates, credit stocks and sector accounts all live here, reported by the Banque de France. |
| BIS (WS_TC, WS_DSR) | REST, open | no | CSV | Fine, and the only source for a household debt-service ratio. |
| Observatoire des crédits aux ménages | PDF | no | report | **Not official.** An industry survey, and the only non-public source in this repo (see §15). |
| Légifrance | — | — | — | **Closed.** 403 to all programmatic access (see §3). |
| UNDP HDR | file | no | csv | Fine, but requires a browser `User-Agent` or it 403s. |
| World Bank | REST, open | no | JSON | Fine. |
| Yahoo Finance (index closes) | REST | no | JSON | Unofficial, used only for index closes. Needs a `User-Agent`, and has a timezone trap (see §8). |
| stooq.com | — | — | — | JavaScript-walled. Abandoned in favour of the above. |

Nothing in this repository needed an API key, a login or a scraper. That is
worth saying plainly, because it is not true of every country.

---

## 3. Légifrance is the one genuinely closed door

Every official French source I touched is readable except the one that
publishes the law. `legifrance.gouv.fr` returns 403 to programmatic requests
regardless of headers, and there is no open alternative that carries the
*text* of a décret.

This matters for exactly one series here, the SMIC, which is set by décret.
The values in `data/macro/smic.csv` therefore come from official secondary
publications (INSEE's series and the social-security bodies' own tables)
rather than from the décrets that enacted them. The numbers are not in doubt
— several independent official sources agree to the centime — but the
primary document is, in practice, unreachable. An API exists on paper
(PISTE/Légifrance) and requires registration and an approved use case, which
is a different thing from open data.

---

## 4. Customs publish trade twice, and the two do not match

The headline goods-trade series (FAB/FAB, used in `data/trade/trade.csv`) and
the product- and destination-level tables (`exports_products.csv`,
`imports_products.csv`, `destinations.csv`) come from the same directorate and
disagree by roughly 1–3%. The detailed tables are *brutes de collecte* —
collection-level data without the adjustments the headline series carries
(estimation for non-respondents, below-threshold trade, corrections).

Neither publication says loudly that you cannot read a level off one and
compare it with the other. In this repo the detailed files are therefore used
**only for composition** — what share of exports is aeronautics — and never
for a level or a total. The product panel also excludes an "others" residual
of about €152bn, which is stated on the panel because a reader who adds the
bars up and gets the wrong total deserves to know why.

---

## 5. data.gouv.fr keeps publishing datasets that have been abandoned

The best example is état 4001, the historical police crime series. The
dataset is still listed, still downloadable, and was last fed in October 2022
with August 2022 data. Nothing on the page says it will never be updated
again. Its own documentation does, however, warn that the figures are
"brutes [...] pas assez fiabilisées en particulier à l'échelle
départementale" — and separately, the unit of count changed mid-series, from
*plaignants* (complainants) to *victimes*, on 1 March 2015.

So the file carries three distinct incompatibilities with the current SSMSI
series: a wider geographic scope, a changed unit of count, and the fact that
its annual figures do not exist as a published total at all — I summed twelve
monthly departmental values to get them. It is committed here as
`violence_pre2016_etat4001.csv` with eleven lines of warnings in its own
header, is never plotted on the same axes as the modern series, and exists
purely so that someone who wants the earlier period can see what the earlier
period actually is.

**Opinion:** an open-data portal should mark a dead dataset as dead. The
cost of not doing it is that the most convenient file is often the one that
should not be used.

---

## 6. COVID surveillance ended mid-series, in three different places

Santé publique France's COVID data has three different last data points
depending on which file you open: 31 March 2023 for the departmental daily
file, 30 June 2023 for the national synthesis, and 19 May 2023 for the care
home component, which simply stops moving while still being published daily.
The legal basis for the underlying data processing expired on 1 July 2023.

The consequences for `data/social/covid_deaths.csv`:

- 2023 is **half a year** in the surveillance columns and a full year in the
  cause-of-death column. One row, two different kinds of year.
- 2024 onwards is empty in the surveillance columns because nothing is
  published, not because nobody died.
- The only COVID figure that exists anywhere for 2024 is CépiDc's 8,549.
  There is none for 2025 and will not be before roughly mid-2027.

And a definitional point that deserves more attention than it gets: **France
never used a 28-day rule.** The surveillance count is every death of a
patient registered as hospitalised for or with confirmed COVID-19, from any
cause, post-mortem diagnoses included — DREES says outright that these
patients "ne sont pas forcément décédés du fait de la Covid-19, mais ils en
ont été porteurs pendant leur hospitalisation". It is a place-of-death count
of infected patients, not a cause-of-death count.

The surprise, which inverts the usual intuition about surveillance versus
certificates: for 2020 and 2021 the **cause-of-death** count is the larger
one (69,249 vs 64,606; 60,895 vs 59,135). Not because certification is
generous, but because the surveillance never saw deaths at home — INSEE puts
the gap at around 22,000 deaths for March 2020 to December 2021. A surveillance
total that excludes an entire place of death is a strange thing to have called
"the death toll" for two years.

One more, uncorrected here: SPF's published total is literally hospital plus
care homes, and the care home component counted residents who died in
hospital as well. So the total plausibly double-counts an unknown number of
people. The CSV reproduces it as published, and says so.

---

## 7. "Flu deaths" is three numbers an order of magnitude apart

For the 2016–17 season France published all of these:

- **2,501** — death certificates naming influenza as the underlying cause
  (CépiDc).
- **14,358** — deaths attributable to influenza, from SPF's regression model
  on all-cause mortality adjusted for influenza activity, RSV and weather.
- **21,200** — raw all-cause excess during the epidemic window.

All three are correct answers to different questions, and the first is not a
lower bound on the second in any useful sense: the model captures deaths
precipitated by influenza that are never coded as influenza. SPF itself warns
that not all of the excess is attributable to flu.

The attributable-mortality model was then **discontinued** after 2019–20. BEH
2022 n°21 says the replacement, electronic death certification, "n'est pas
comparable à celui utilisé jusqu'en 2019-2020". So the middle column of
`flu_deaths.csv` ends in 2020 — an end of publication, not a gap in my
retrieval. Electronic certification, meanwhile, covered only about half of
national mortality at the end of 2024, with enormous regional variation (25%
to 67%), which makes it useless for a national total even where it is current.

Three weaker spots worth stating: SPF revised three earlier seasons downward
in 2025 without explaining why (this file keeps the original values and says
so); three seasons' excess figures exist only as parenthetical comparisons in
a later bulletin, with no number at all in their own seasonal reports; and for
2023–24 one SPF publication reports no national excess at the epidemic peak
while another gives 8,100.

---

## 8. Things that look like data problems and are not

**The 2019 fall in the tax burden.** About 0.9 point, and entirely
definitional: the CICE stopped being a tax credit booked as spending and
became a cut in employer contributions, which lowers the numerator without
any change in tax policy. Drawn unannotated it is the largest "tax cut" of
the period, and it never happened. The plate marks it on the line.

**Reserves quadrupling.** France's official reserve assets are about 80% gold
and the holdings have not changed since 2009. The rise is the gold price,
revalued at market. An accumulation story read off that line would be
entirely invented.

**Recorded violence rising after 2017.** Substantially a change in the
propensity to report rather than in the underlying rate. This is the SSMSI's
own reading, not a sceptical gloss, and the caveat sits next to the rising
line rather than in a corner of the plate.

**The CAC 40 "closing a month early".** Not a data problem at all but mine:
Yahoo stamps a monthly bar at the start of its month in the exchange's local
time. Read as UTC, midnight in Paris lands on the last day of the previous
month, so every year-end close came back as January's. The S&P 500 is immune,
because New York's offset is negative — which is exactly why the series used
to sanity-check the other one could not reveal the fault. It is now pinned by
a test.

**The 2014 step in all-cause deaths.** Mayotte enters the état civil series.
INSEE publishes both figures for that year (559,293 and 558,727), so the step
is tiny and entirely explicable — and still a break rather than a trend.

---

## 9. Where INSEE is better than its reputation

Two things worth crediting, because they removed work rather than adding it.

**Retropolation.** At every base change INSEE recomputes the whole national
accounts backwards. Base 2020 runs unbroken from 1959. There is no
vintage-splice problem in the French fiscal series at all — which is a sharp
contrast with the equivalent Brazilian work, where the tax burden needs a
methodology break drawn on it.

**Documentation of what a series is not.** The scope notes are specific and
easy to find. France versus metropolitan France (`FR` versus `FRM` at
Eurostat) is consistently labelled; the overseas departments are either in or
out and the file says which. Every geography in this repository is `FR`,
including the DROM, and the one place that differs — the abandoned état 4001
file, which also includes the COM — says so in its header.

---

## 10. Series that are computed here, not published

Honesty requires a list. Each of these is arithmetic on published values, and
each is marked on its plate or in its manifest entry:

- **Primary balance** = deficit + interest paid. (Identity checked by a test.)
- **Homicide rates per 100k** — both the SSMSI and CépiDc rates, from counts
  over population. Neither institution publishes the rate.
- **Excess mortality** vs the 2015–2019 mean. Deliberately crude: no age
  standardisation, so part of every bar after 2019 is simply a larger and
  older population. The panel says this.
- **Trade openness** = (exports + imports) / GDP, goods only. Services would
  add about a third.
- **The état 4001 annual totals** — twelve monthly departmental values summed.
- **GDP per capita in dollars** — nominal GDP over population over the
  average exchange rate.
- **The Eurostat Gini rescaled** from 0–100 to 0–1, so it shares an axis with
  INSEE's. A rescaling, not a conversion: the two remain different surveys.
- **Annual averages of the monthly bank interest rates.** The ECB publishes
  the monthly observations only. The December value is carried alongside, so
  a reader who wants an end-of-year rate does not have to accept an average
  for one.
- **Credit stocks in billions**, converted from the ECB's millions. The
  growth rates beside them are *not* computed: they are the ECB's own
  notional-stock growth, because a difference of stocks would attribute a
  securitisation to borrowers.

---

## 11. Pairs that are never spliced

Kept as separate columns, drawn as separate lines, and documented in both the
manifest and the page copy:

| Pair | Gap | Why they differ |
|---|---|---|
| Tax burden: INSEE vs Eurostat | ~2.6pt in 2024 (42.7 vs 45.3) | Eurostat counts imputed employer social contributions — pensions the state owes its own staff without funding them. |
| Gini: INSEE ERFS vs Eurostat EU-SILC | small but systematic | Tax-and-benefit administrative file versus a household survey. |
| Homicides: SSMSI vs CépiDc | varies | Police record by force that recorded it versus death certificates by year of death. An attempted homicide is in neither; a death recorded one year may be certified the next. |
| Policy rate: DFR vs MRO | large after 2014 | The deposit facility rate steered policy 2014–2022 while the main refinancing rate sat at zero. The MRO fixed-rate series also only starts in October 2008 — before that, variable-rate tenders with a minimum bid rate, a different instrument. |
| All-cause deaths: INSEE vs CépiDc | ~2,100 in 2024 | Civil registration versus certificates actually received and codable. CépiDc's own total is the right denominator for a CépiDc numerator. |
| Household debt: four measures | large | Consolidated against non-consolidated, loans against all debt instruments, GDP against adjusted disposable income. See §17. |

The last one is the subtle one: dividing a CépiDc cause-of-death count by an
INSEE total understates every share, for no reason, which is why both columns
are in the file.

---

## 12. Projections supersede each other and must not be mixed

INSEE's 2021–2070 population exercise put the peak at 2044, around 69.3M. The
newer *Projections de population 2026* puts it at 1 January 2037, at 69.77M.
That is a seven-year move in the single most quoted number of the exercise.

Both are official; only one is current. `data/social/population.csv` holds one
exercise, not a blend, and the plate's dashed segment is one model's output
rather than a consensus. Deaths overtook births in 2025 for the first time
since the Second World War, which is observed rather than projected, and is
most of why the peak moved.

---

## 13. Where the international comparisons are weakest

The two reputational indices on plate 07 are the least solid data in the
repository, and they are drawn with that said on the panel.

- **WEF Global Competitiveness Index**: the scale changed from 1–7 to 0–100
  with reweighted pillars in 2018, so France's apparent jump from 22nd to
  17th is mostly the methodology. The rank denominator moves between 125 and
  141 economies. Rankings were "paused" in 2020 and never resumed, so the
  series simply stops.
- **Transparency International CPI**: 0–10 through 2011, 0–100 from 2012, and
  TI states that only 2012 onwards are comparable. The chart rescales the
  earlier values by ten so the panel has one axis, and says so.

**Opinion:** both belong on the plate because they are what gets quoted, and
both deserve the caveat printed next to them rather than in a footnote.

---

## 14. The Banque de France was simply unreachable for a day

While the credit series were being compiled, `banque-france.fr`,
`particuliers.banque-france.fr` and `acpr.banque-france.fr` all 302'd every
path to `/maintenance/maintenance.html` for the better part of a day. Not an
outage of a single page: the whole publication estate, including every PDF of
the surendettement surveys and the ACPR's reports on housing finance.

`webstat.banque-france.fr`, the statistics portal, stayed up — which is the
right thing to have survive, and also not where the methodology is written
down.

Everything taken from a Banque de France or ACPR document during that window
was therefore read from Internet Archive captures, and `SOURCES.yaml` records
both the original URL and the archive one. The figures reconcile with
Webstat where the two overlap. **Opinion:** a national central bank's
publication archive should not be a single maintenance window away from
being uncitable, and it is worth re-verifying those PDFs against the live
site.

The deeper problem is not the outage. **No long machine-readable
surendettement series exists anywhere.** Webstat's series starts in January
2019. Everything before that is a number printed in an annual survey PDF,
and the five-year summary table that gets you back to 2007 appears in exactly
one edition — the 2011 *baromètre*. For 2006, earlier editions count
*dossiers recevables* over a partial year, which is a different quantity, so
that cell is empty rather than back-calculated from a published percentage
change.

And the population definition changed in 2022, which is why the median debt
per dossier only exists from then.

---

## 15. One non-official series, and why it is here

`data/credit/credit_holding_ocm.csv` — the share of households holding any
credit — comes from the Observatoire des crédits aux ménages, a survey run by
the banking federation and the finance-houses association. It is the only
series in this repository that is not from a public institution, and it is
labelled as a survey everywhere it is drawn.

It is here because nothing official measures it, and because it is the one
thing the stock and rate series structurally cannot tell you: **the stock of
credit can grow while fewer households borrow.** It has. The share holding
any credit fell from 47.8% in 2017 to 40.4% in 2025, a low since the survey
began in 1989, while the outstanding stock rose from about €1,200bn to
€1,741bn. Those are not in tension; they are the same thing seen from the
two ends. Omitting the survey would have left only the end that looks like
growth.

---

## 16. Rates: three different "interest rates", and only one is in here

The ECB's MIR series are the *Annualised Agreed Rate / Narrowly Defined
Effective Rate*. The French statutory *TAEG* includes arrangement fees,
compulsory borrower insurance and guarantee fees, which the NDER excludes.
And the *taux d'usure* — the legal ceiling, published quarterly by the Banque
de France — is set against the TAEG.

So an NDER of 4.0% is not comparable with a usury ceiling of around 6%, and a
chart that puts them on one axis is simply wrong, in a way that looks
informative. The usury rate is not in any SDMX dataflow — it is a table in
the *Journal officiel* — and it is not in this repository.

Two more things about MIR worth knowing before reading a French rate series:

- **"New business" includes renegotiations.** The 2016–17 and 2020–21
  renegotiation waves pull the average down for a reason that is not new
  lending.
- **France has no per-fixation volumes in MIR**, so you cannot compute a
  volume-weighted rate or a fixed-rate share from it. The fixed-rate share in
  these notes is the ACPR's own figure (98.1% of the outstanding stock in
  2023, 98.5% in 2024), from its report on housing finance — a primary
  source, not an inference from the rate series.

That last number is the hinge of the whole credit plate. Rates on new
housing loans roughly tripled between 2021 and 2024, from 1.15% to 3.39%,
while the rate carried by the *existing* stock moved from 1.56% to 1.99% —
and the BIS debt-service ratio did not move at all, sitting at about 6% of
income across the entire twenty years including the shock. A country whose
mortgage book is 98.5% fixed-rate transmits a rate shock to new borrowers and
almost nobody else.

---

## 17. Household debt has four legitimate definitions

`household_debt.csv` carries four, in separate columns, and they differ by
consolidation, instrument scope, denominator and vintage:

- **ECB QSA, loans as % of adjusted gross disposable income,
  non-consolidated** — this is the *taux d'endettement des ménages* the
  Banque de France communicates. 70.6% in 2006, peaking at 102.2% in 2021,
  90.8% in 2024.
- **ECB QSA, % of GDP** — same numerator, different denominator.
- **Eurostat `nasa_10_f_bs`, % of GDP** — carried consolidated *and*
  non-consolidated in two columns rather than one.
- **BIS credit to households, % of GDP**, plus the BIS debt-service ratio.

No consolidated debt-to-income ratio exists for France in QSA at all, which
is worth knowing before going looking for one. Eurostat's `tipsd21`
indicator, which the documentation still references, is withdrawn and returns
404; its `PC_GADI` unit exists in the metadata but serves no values for
French households.

**The trap.** Every leverage ratio in that file fell between 2023 and 2025
while over-indebtedness filings rose by about 36%. Both are real. The ratios
fell because nominal incomes grew while the credit flow stalled — stock
growth went from 11.5% in 2006 to 0.3% in 2024, with housing lending actually
negative — and the filings are a count of households that reached a statutory
insolvency commission, which is a different population from the aggregate
denominator. A plate showing only one of the two would mislead in whichever
direction it chose, which is why they are on the same panel with the caveat
printed under it.

One more: the securitisation gap. The stock on the banks' own books was
€1,556bn at the end of 2025; adjusted for loans sold on or securitised it was
€1,741bn. Both are published by the ECB, and a difference of unadjusted
stocks would attribute a securitisation to borrowers — which is why the
growth rates in that file are the ECB's own notional-stock growth and not a
difference of the levels beside them.

---

## 18. If I were doing this again

- **Start from Eurostat for anything harmonised, and go to the national
  source for anything definitional.** The harmonised copy is easier to fetch
  and is sometimes not the number the national debate uses. Both belong in
  the file.
- **Write the caveat into the CSV, not only into the manifest.** The files
  with leading `#` comments are the ones I trust myself with six months from
  now. A note in a separate document is a note someone will not read.
- **Treat a partial year as a different kind of value, not a smaller one.**
  The worst bug in this build drew a half-year of trade as an annual total: a
  fake 50% collapse in exports, perfectly plausible-looking, caught by
  eye. The fix is a helper that drops incomplete years from every annual
  flow, plus a test.
- **Pin a fetcher's quirks with a test, not a comment.** The timezone bug in
  §8 would have survived any amount of commenting.
- **Never average two definitions.** It produces a third number that nobody
  published and nobody can check.
- **When two true series point opposite ways, put them on one panel.**
  Leverage ratios falling while insolvency filings rise is the clearest case
  here. Either one alone reads as the whole story, and neither is.
- **Archive the PDF when you read it.** A central bank's whole publication
  estate was behind a maintenance page for a day. The series that lives only
  in a PDF is the fragile one, and it is usually the oldest and most
  interesting part of the record.

---

*Compiled 21 October 2026, against the data available on that date.*
