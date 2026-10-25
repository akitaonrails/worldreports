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

From 2015 the two lines differ by 2.1–2.8m and **neither is wrong**. They
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
| other | ЖКХ, охрана окружающей среды, культура, СМИ, физкультура, межбюджетные трансферты |

**The classification changed in 2013** and the file carries that seam
inside each column rather than across rows. Before 2013 three combined
sections carried the money and their sub-rows were blank; from 2013 the
sub-rows carry it and the combined rows are blank. Each column is built
from whichever label the publisher actually filled in that year, so a 2006
cell and a 2021 cell in the same column measure the same section. Two
consequences a reader must know: **health bundles sport before 2013**, and
**culture_media excludes media from 2013** because media became its own
section. The fourteen sections **reconcile to the published expenditure
total within 0.2bn in every year 2006-2021** — asserted on every fetch,
and it is the check that exposed the split in the first place.

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
  roubles across years: from the staged vintage, nominal GDP in 2025 is
  8.0× its 2006 level while the physical-volume index is 1.56×, so a
  nominal-rouble line spanning the window measures the price level, not the
  economy. (Chaining the published deflator gives 5.9× across the same
  years; nominal over real gives 5.1×. The two are the publisher's own two
  routes and they do not reconcile exactly, which is another reason no
  level is drawn in current roubles.) Levels are in constant prices, shares
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

`country.yaml`'s four bands are dated on the staged quarterly index
(`macro/gdp_quarterly.csv`, year-on-year), so each is a run of consecutive
quarters the publisher's own index shows negative:

- **2008 Q4 – 2009 Q4** — five negative quarters; Q4 2008 = −1.32 and Q2
  2009 = −11.15. The global crisis, oil from $147 to $40.
- **2015 Q1 – 2016 Q1** — five negative quarters; Q2 2015 = −3.09. The oil
  collapse and the rouble's halving in December 2014.
- **2020 Q2 – 2021 Q1** — four negative quarters; Q2 2020 = −7.32. COVID-19.
- **2022 (calendar year)** — the ANNUAL index only, −1.44%. The quarterly
  series **ends at 2021 Q4**, so this is the one band whose quarters are
  not observable in the staged vintage. It is labelled accordingly.

**Not banded:** 2014 Q1 is a single negative quarter (−0.05%) and annual
2014 is +0.74% — a dip, not a recession. The annexation of Crimea in March
2014 is an annotation on the population panel, not a recession band on the
output panel, because the output index does not turn negative with it.

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

## 14. Running the fetchers on this network

`make C=russia fetch` runs `fetch_rosstat.py` with TLS verification **on**
and it will stop with the certificate message described in
`DISCOVERY.md`: rosstat.gov.ru's chain is signed by the Russian Trusted
Root CA, which this host does not carry. Either install that root in the
host trust store (the correct fix), or run that one fetcher with
`ROSSTAT_INSECURE=1` — the flag changes the transport, never a number, and
the sidecar records which mode produced it. The other four fetchers need
nothing.

## 15. Shared-code needs: what was resolved, and what is still open

Phase A touched nothing outside `countries/russia/` and reported three
things `core/` needed before a rouble could be drawn or written. Two of the
three landed on `main` with the batch (`57b818e`, `2ffdb0f`) and are in
this lane after the rebase:

1. **`CURRENCY_AFFIX` now has a `RUB` block** — the rouble sign after the
   amount in Russian (`5 627 млрд ₽`) and `RUB` before it in English and
   Portuguese — so `tests/test_numbers.py::…write_its_own_money[russia]`
   passes, and the headline strip writes 2,56 трлн ₽-shaped figures in ru
   and US$ in the other two.
2. **`core.numstyle` now carries `ru`**: comma decimal, non-breaking-space
   thousands (CLDR `ru`), so `12 345,67` is written the same way on a plate
   and on a card. `country.yaml` still declares no `number_style`, because
   Russia does not depart from its language's base style.
3. **`core.i18n`'s Russian unit words** (`млрд`, `трлн`, `млн`, `тыс.`,
   `п.п.`) are in place; no further unit work was needed for the ru plates.

**Two shared comparison scales are still too narrow for verified Russian
data.** Both are real readings, not errors, and neither is widened in
country code (AGENTS.md: the atlas-wide range lives in `core/spine.py`):

| slot | shared range | Russian reading | what the plates do meanwhile |
|---|---|---|---|
| `fiscal.balance` | −35 … **+8** | primary balance **+8.49%** of GDP (2006) | the bars and the labelled federal line are drawn, the primary balance is stated in the panel's foot, unclipped |
| `security.suicide` | 0 … **40** | suicide rate **41.44** per 100,000 (2006) | the canonical line starts in 2007 and the 2006 point is drawn in the chapter's lens, which has its own scale, and named on the panel |

Widening `fiscal.balance` to +9 or +10 and `security.suicide` to 45 would
let both panels draw their full canonical series; that is one edit in
`core/spine.py` and a regeneration of every country carrying the two
topics, which is the orchestrator's call, not this lane's.

## 16. Phase B: what the plates draw, and on which denominator

Twelve plates, one per spine topic, every panel claimed by slot key. The
conversions and the denominators, so a reader can re-derive any number:

| panel | unit drawn | conversion and denominator |
|---|---|---|
| economy.growth | % per year | Rosstat's published index minus 100; no conversion |
| economy.gdp_per_person | US$ current | the publisher's own figure (World Bank GDP over the UN population) — not Rosstat's rouble per-capita, which is not staged |
| economy.inflation | % per year | Rosstat Dec/Dec as the line, World Bank annual average beside it; two series, never merged |
| economy.unemployment | % of labour force | the ILO modelled estimate as published; not a survey |
| world.gdp, world.reserves | US$ bn | staged US$ ÷ 1e9 |
| demography.population | index 2006 = 100 | each line indexed on its own 2006 value; Rosstat and UN lines separate |
| demography.fertility | children per woman | as published |
| demography.birth_death | per 1,000 | published rates; no denominator applied |
| demography.natural_migration | per 1,000 | the components file's own thousand counts ÷ **its own 1 January population** (same publication, same perimeter); 2014 blank because suppressed |
| people.gini, people.poverty | 0–100 / % of people | as published; the national line and the World Bank line are two lines |
| people.lens | index 2006 = 100 | Rosstat's Dec/Dec CPI chained from 2006 — derived, and labelled |
| fiscal.* | % of GDP | IMF WEO general government as published |
| fiscal.balance (gold line) | % of GDP | Minfin's federal non-oil-and-gas balance ÷ Rosstat's nominal GDP, same year. 2025: −14,103.4bn ÷ 214,261.0bn = −6.58% |
| spending.* | % of GDP | Minfin's 14 functional sections ÷ Rosstat's nominal GDP, mapped onto the spine's seven groups; the seven sum to the published federal expenditure (18.4% of GDP in 2021) |
| spending.investment | % of GDP | World Bank GFCF (whole economy), not the budget |
| trade.* | % of GDP | World Bank national accounts, goods and services |
| trade.lens | US$ bn | (exports − imports) ÷ 100 × World Bank GDP in current US$; derived |
| markets.policy_rate | % | Bank of Russia key rate, **annual mean of the daily rate**; the peak is a separate column and is annotated, not plotted |
| markets.bond_10y | %, annual average | the Bank of Russia's zero-coupon curve, 10-year tenor, mean of the daily readings |
| markets.currency | index 2006 = 100 | 27.1355 ÷ the year's mean rate × 100, per `core.rates.fx_index` |
| markets.equities | index 2006 = 100, in US$ | IMOEX rouble mean ÷ the same year's official mean rate, then indexed on 2006 |
| credit.household_debt | % of GDP | BIS Q4 reading |
| credit.lending_rate | % | the Bank of Russia's new-loan rate, annual mean; the workbook starts in 2014 and the years before it stay absent |
| credit.npl | % of loans | the World Bank's FS indicator, 2008–2023 |
| credit.lens | percentage points | the new-loan rate minus the key rate, two Bank of Russia series |
| security.* | per 100,000 | the publisher's own rates; no denominator applied |
| mortality.death_rate | per 1,000 | the published rate |
| mortality.lens | years | life expectancy, as published |
| migration.net | per 1,000 | the UN/WB modelled net migration ÷ **the same series' population** (UN WPP), not Rosstat's |
| migration.foreign_born | % of population | UN DESA migrant stock ÷ the UN population |
| migration.lens | persons | the model's own level, unrated |

**Two marks, and no more.** `events.py` carries the December 2014 rouble
halving (a rule on the currency panel, because the annual mean puts the
devaluation in 2015) and the 2014 perimeter change (a rotated rule on the
population panel). The four contractions are recession bands from
`country.yaml`, dated on the quarterly index, and are deliberately not
repeated as event marks. Every band is drawn unlabelled: with Russia's four
bands, one of them the long "sanctions regime (annual)", the captions
collide with each other and with the panel title, so the economy panel's
note names them and `ui.json` explains the convention on every page.

**Lenses, and why each.** `people` chains the national CPI into a price
level, because "what a rouble buys" is the country's own inflation story and
no canonical slot can hold it. `trade` converts the surplus to dollars,
because the canonical slot is a share and the level is what pays for
imports. `credit` draws the margin over the key rate, which is where the
2022–2025 rate regime actually shows. `security` sets 2006 against the last
year each cause is published, which is also where the 41.4 suicide reading
that exceeds the shared scale is drawn. `migration` shows the same model in
persons, since the rate flattens a 766,000-person inflow into 5.3 per 1,000.

**What is still pending, and why** — each also stated in `ui.json`
`unavailable` in all three locales: EMISS 403, `data.gov.ru` no route,
customs statistics suspended (so export destinations), UN Comtrade with no
Russian rows for 2022–23, the Transparency International CPI 403, COVID-19
and excess deaths (no official count or cause series reachable), the minimum
wage (research incomplete), the federal spending sections after 2021,
Rosstat's LFS unemployment, the registration-system migration totals
(deliberately rejected as a proxy beside the model) and public investment
(not staged).

**Verification of this phase.** `python3 -m core.render russia` writes 36
plates (12 × 3 locales) with no untranslated string; `core.thumbs` writes 36
thumbnails; `core.provenance` records the 29 curated CSVs the plates read,
and the one curated file no plate reads is `macro/gdp_quarterly.csv`, which
is the evidence the recession bands are dated on and is cited as such on the
economy panel. `tests/test_layout.py` reports **zero** faults in `russia/en`,
`russia/ru` and `russia/pt`. The full suite is green: 2378 passed.
