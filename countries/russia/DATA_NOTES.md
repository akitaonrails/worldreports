# Russia — data notes

What these numbers are, what they are not, and the judgement calls that
were made turning publishers' files into the committed CSVs. `SOURCES.yaml`
is the manifest and carries the per-series verification; `DISCOVERY.md` is
the record of what each publisher answered. This file is the reasoning.

Read it before drawing anything. Three of these decisions change what a
plate can honestly say.

---

## 1. The territorial seam, which is the largest thing in this country's data

Russia annexed Crimea and Sevastopol in March 2014 and its statistical
system counts them from then on. Rosstat's population series steps from
**144.0m (2014) to 146.7m (2015)** — +2.7m, of which about 2.3m is
territory and the rest is natural and migration change. The World Bank /
UN series steps by 0.4m across the same years, because the UN carries
Russia on a different perimeter.

From 2015 the two lines differ by 2.3–2.7m and **neither is wrong**. They
are two territories. The plate draws both, labelled, and the gap is
annotated as the annexation rather than left for a reader to interpret as
2.7m of migration.

The seam does not stop there. From **2022** Rosstat's own footnote on the
national-accounts and population workbooks reads "без учёта статистической
информации по Донецкой Народной Республике, Луганской Народной
Республике, Запорожской и Херсонской областям" — the figures exclude the
four oblasts Russia claimed and annexed in September 2022. So the 2022+
perimeter is **narrower** than the 2015–2021 one. A level compared across
2021→2022 is comparing two territories, and no plate in this country does
that without saying so.

## 2. Two CPI definitions, both published, both correct

Rosstat's headline CPI is December-to-December. The World Bank's
`FP.CPI.TOTL.ZG` is the **annual average** change. They differ every year
and the difference is largest in the years that matter:

| year | Rosstat (Dec/Dec) | World Bank (annual average) |
|---|---|---|
| 2008 | 13.28% | 14.11% |
| 2015 | 12.91% | 15.53% |
| 2022 | 11.94% | 13.74% |

Both are staged, in `macro/cpi.csv` and `macro/economy.csv`, and the
economy plate draws the national line as the headline with the average
beside it. A single line stitched from the two would make 2015 look like
either 2.6 points of extra inflation or 2.6 points less, depending on
which year the seam landed on.

## 3. Three fiscal perimeters, not one

- **Federal budget** (`fiscal/federal_budget.csv`, Ministry of Finance):
  cash execution, one level of government, in roubles. 2024 revenue
  36,708.6bn, expenditure 40,180.5bn, deficit −3,471.9bn.
- **General government** (`fiscal/fiscal.csv`, IMF WEO): accrual,
  consolidated, % of GDP. 2024 revenue 35.27% of GDP, expenditure 36.87%.
- **The non-oil-and-gas deficit** (same Minfin file): −14,103.4bn in 2025,
  which is the number Russian fiscal argument is actually about, because
  it is what the oil revenue is hiding.

The spine's fiscal slots are general government. The federal line rides
beside it, labelled, in roubles or as a derived share of GDP — never
spliced, and never converted into a "general government" figure by adding
anything.

## 4. Spending: the national classification, and where it stops

`spending/budget_function.csv` is the Ministry of Finance's 14 functional
sections in billion roubles. **It is not COFOG** and the mapping onto the
spine's seven groups is approximate:

| spine group | Russian sections |
|---|---|
| social protection | Социальная политика |
| health | Здравоохранение (section 2.9 bundles sport until 2011) |
| education | Образование |
| general public services | Общегосударственные вопросы + Обслуживание долга |
| economic affairs | Национальная экономика |
| defence + public order | Национальная оборона + Национальная безопасность и правоохранительная деятельность |
| other | ЖКХ, охрана окружающей среды, культура и СМИ, физкультура, межбюджетные трансферты |

Two honest caveats. **The breakdown stops in 2021**: the publisher's annual
workbook answers 200 and its totals run to 2025, but the 2022–2025 section
columns are empty, because federal spending by section has not been
published since the 2022 classification of budget data. And
**межбюджетные трансферты are not a function**: they are transfers to
other budgets that COFOG would allocate to whatever they fund. They sit in
"other" and the note says so, because putting them anywhere else would
invent an allocation the publisher does not make.

## 5. Markets: the 2022 break, and why the mean and the peak are two columns

The key rate went from 9.50% to **20.00% on 28 February 2022** and back
down within three weeks. An annual mean of 10.55% for 2022 therefore
describes neither the panic nor the year — which is why
`markets/key_rate.csv` carries `key_rate_pct` (the mean, the line) and
`key_rate_pct_peak` (the highest single day, the annotation). The plate
carries 20.00% as a note on the line, not as a point on it.

The key rate itself **begins on 13 September 2013**. 2006–2012 is a hole.
It is not filled by extending the series backwards onto the refinancing
rate: the two are different instruments that happened to be equal for a
period, and a line with a seam at 2013 would be read as a policy change
that did not happen.

Equities: MOEX suspended trading from **25 February to 24 March 2022**.
The 2022 file has 235 sessions against ~250 in a normal year and the panel
draws a gap. `imoex_usd_avg` is an arithmetic conversion of a rouble price
at the official rate — from 2022 most foreign holders could not trade the
underlying, and the number is a conversion, not a market observation for
them. It is drawn, and the note says what it is.

The rouble's official rate was fixed by capital controls for part of 2022.
`markets/usd_rub.csv` is the Bank of Russia's official rate throughout, so
the 2022 stretch is an administered price and is annotated.

## 6. Population: two Rosstat releases that disagree, and which one is used where

Rosstat publishes the long annual population series
(`popul_1897+.xlsx`) and, separately, a year's population-change table
with its components (`Popul components_1990+.xlsx`). They are different
vintages and they disagree — at the 2020-census rebase the components
file's closing stock jumps from **145,557.5 (2021) to 146,980.1 (2022)**,
+1.4m of revision in one step, while the long series reads 147.4 and 147.0.

The decision: **`demography/population.csv` is the long series** (one
vintage, consistent ratios, used for the index and for per-person
figures), and **`demography/components.csv` carries its own 1 January and
31 December stocks**, which are the publisher's own denominators for its
per-1,000 rates. Natural increase and net migration are divided by the
components file's own population, never by the other file's. That keeps
each rate inside one publication.

The components file also **suppresses 2014** — the component columns are
"…" in the year the territory changed, with only the closing stock given.
That is a hole and is left empty.

## 7. Unemployment is modelled, and says so

`macro/economy.csv` carries `SL.UEM.TOTL.ZS`, the ILO **modelled**
estimate as the World Bank publishes it (2009: 8.30%, 2025: 2.13%). It is
not the Russian labour-force survey headline — Rosstat's LFS page answers
and its own workbooks are a Phase-B follow-up (`meta.pending`). Every
plate that draws it labels it "ILO modelled". Calling it "unemployment"
without that word would attribute a model's output to a survey.

## 8. Series that stop, and stay stopped

These are findings about the sources, not fetch failures:

| series | last year | why |
|---|---|---|
| homicide (`security.csv`) | 2021 | UNODC/WHO rows end; national publishers unreachable |
| suicide | 2021 | same |
| road deaths | 2019 | WHO rows end |
| bank NPL (`credit/npl.csv`) | 2023 | World Bank FS indicator has no 2024-25 Russian row |
| Gini (`people/gini.csv`) | 2023 | household survey; Rosstat's own is not machine-readable here |
| federal spending by section | 2021 | not published since the 2022 classification of budget data |
| IMF revenue/expenditure | 2024 | WEO October 2026 vintage; 2025 carries only balance and debt |
| migration totals (Rosstat) | 2023 | not staged — see below |
| COVID-19 deaths, excess deaths | — | no official series reachable; see `meta.pending` |

Nothing interpolates across any of them.

**Rosstat's migration totals** (`Itog_migr_1990-2023.xlsx`, arrivals and
departures counted by the registration system, 1990–2023) were downloaded
and inspected and are **deliberately not staged beside the modelled UN
net-migration series**. The registration system's coverage of emigration is
known to be weak, and the two measure different things: putting them on
one panel would invite a reader to subtract them. The modelled series is
what is drawn, labelled as modelled; the national file is recorded here so
a later pass can stage it as its own labelled line if it is wanted.

## 9. Which population denominator each rate uses

- **Deaths, homicides, suicides, road deaths:** the rates are the
  publisher's own (`per 100,000`), so no denominator is applied here and
  the UN perimeter is implied throughout.
- **Birth and death rates per 1,000** (`demography/vitals.csv`): published
  rates, US/UN perimeter.
- **Natural increase and net migration per 1,000**: computed from the
  components file's own population, thousand people, so the rate is
  Russian-perimeter.
- **GDP per person** (`world/gdp_per_person.csv`): the World Bank's own
  figure, i.e. US$ GDP over the UN population. Not Rosstat's per-capita
  in roubles, which is in the Rosstat workbook and not staged.
- **Household debt and every fiscal share of GDP:** the BIS/IMF use their
  own GDP, which is the same national-accounts concept on the same
  perimeter as the World Bank's.

## 10. Currency and units

- Roubles are **nominal** everywhere, and nothing is drawn in nominal
  roubles across years: the deflator takes the 2025 price level to about
  3.7× the 2006 one, so a nominal-rouble line spanning the window measures
  the price level, not the economy. Levels are in constant prices, shares
  of GDP, or dollars, and each says which.
- The Ministry of Finance file is in **billion roubles**; Rosstat's GDP is
  in **billion roubles**; the Bank of Russia's lending rate is a
  percentage; the BIS is a share of GDP. No unit conversion happens
  anywhere except the per-1,000 rates and the USD index, both documented
  above.
- `imoex_usd_avg` uses the annual mean official rate from
  `markets/usd_rub.csv`, deliberately the same number the currency panel
  draws, so the two panels cannot disagree about a year.

## 11. What is not drawn, and why

- **Trade by partner** — customs statistics suspended in 2022, customs host
  unreachable, UN Comtrade has no Russian rows for 2022–2023. Pending.
- **Corruption Perceptions Index** — the TI CDN returns 403 from this
  network (a network block, not a dead endpoint; the Ukraine lane hit the
  same one). Pending.
- **Minimum wage** — the МРОТ is statutory, set by federal law; no
  machine-readable time series was located in this pass. Incomplete
  research, recorded as such, not as absence.
- **COVID-19 deaths and excess deaths** — no official series reachable;
  excess deaths need counts, not rates.
- **A COFOG spending breakdown** — Russia does not publish COFOG, and the
  national classification stops in 2021.
- **Quarterly GDP expenditure breakdown** — Rosstat stopped publishing the
  detailed quarterly breakdown; the quarterly physical-volume index
  continues and is what the recession bands are dated on.

## 12. Recession bands

`country.yaml`'s four bands are dated on Rosstat's own annual and quarterly
GDP vintage, not on a narrative:

- **2008 Q3 – 2009 Q3** — the global crisis, oil from $147 to $40.
- **2014 Q3 – 2016 Q4** — the oil collapse, the rouble halving in December
  2014, the first sanctions round, and the 2015–16 contraction
  (annual −1.97% and +0.19%).
- **2020 Q2 – 2020 Q4** — COVID-19 and the lockdown quarter.
- **2022 Q2 – 2023 Q1** — the sanctions regime, on annual −1.44%.

The 2014 band starts in Q3 rather than at the annexation (Q1) because the
output index turns negative in Q3; the annexation is annotated separately.

## 13. Verification performed

Every staged series carries a `VERIFIED` line in `SOURCES.yaml` with at
least one known observation pinned. The anchors that would catch a unit or
scaling error, and where each was checked a second way:

| anchor | file value | second route |
|---|---|---|
| GDP growth 2022 | −1.44% | World Bank −1.44 and IMF −1.44: three publishers, one number |
| nominal GDP 2006 | 26,917.2bn RUB | World Bank NY.GDP.MKTP.CN, same order after the 2006 average rate |
| CPI 2015 | 12.91% (Dec/Dec) | WB annual average 15.53 — the documented definitional gap, not a discrepancy |
| population 2014→15 | 144.0 → 146.7m | the +2.7m step is the annexation; the UN series has +0.4m |
| key rate 28.02.2022 | 20.00% | Bank of Russia's own daily rows; the news record |
| USD/RUB 2014 | 38.60 mean | the December 2014 spike to ~68 is inside the daily rows |
| federal deficit 2024 | −3,471.9bn RUB | the Ministry's own annual release: −3.49trn |
| household debt 2024 | 21.5% of GDP | BIS Q4 reading; Russia's ~21-22% is the commonly cited share |

The fetchers assert these on every run and refuse to write a sidecar whose
anchors fail. A silent revision, a unit change or a truncated payload
therefore fails at fetch time rather than landing in a published chart.

## 14. Known shared-code needs (reported, not changed here)

- **The `ru` number style.** `core/numstyle.STYLES` does not yet carry
  `ru`, so `tests/test_numbers.py` fails for this country (as it does for
  `pl`). The orchestrator is adding it centrally; nothing in this lane
  touches `core/`.
- **`RUB` currency forms.** `core.sitebuild.CURRENCY_AFFIX` needs a RUB
  entry for every style this country publishes (`ru`, `en`, `pt`) before
  cards can format a rouble figure.
- Neither is a Phase-A blocker: no plate or card is drawn in this phase.
