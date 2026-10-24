# Field notes on Argentina's official data

These are working notes, not documentation. `SOURCES.yaml` says where every
number in this atlas came from; this file says what it was like to go and
get it, what I trust, what I do not, and which decisions a reader should
know about before reading a chart. It is written as I went, so it is
opinionated in places.

---

## The short version

Argentina publishes more open data, through better machinery, than most
countries in the region — and a decade of it cannot be used. Those two
facts are not in tension. The machinery (`apis.datos.gob.ar`) is genuinely
good. The 2007–2016 statistics it serves are the output of an intervened
agency, and the state itself said so in 2016. Nearly every editorial
decision in this repository follows from that one break.

---

## 1. The gateway: `apis.datos.gob.ar/series`

Argentina has something Brazil does not: **one API in front of every
agency**. INDEC, BCRA, Hacienda, Ministerio de Seguridad, Energía — all of
them publish time series into a single catalogue with a single query
grammar. No per-agency SOAP endpoint, no per-agency authentication, no
per-agency date format. `?ids=9.1_PPC_2004_A_22&format=json` works the same
whether the series is a quarterly GDP aggregate or a monthly homicide
count.

This is the best thing about the Argentine data estate and it deserves to
be said plainly before the complaints start.

What it costs you:

- **The search API is close to useless for discovery.** Querying it for
  "pobreza" or "deuda" returns a scored mess, paginated, with no way to
  filter by publisher reliably. What worked was downloading the full
  metadata dump — 34,741 rows — and grepping it offline. Every series ID in
  `fetch_datos_gob.py` was found that way. If you are starting from
  scratch, do that first; do not page the search endpoint.
- **A dead series looks exactly like a live one — and the catalogue
  actively says it is alive.** The metadata dump carries a
  `serie_discontinuada` flag and a `serie_valores_cant` count, which is
  more than most catalogues offer. For the annual tax series
  `142.1_TOTAL_2001_A_26` they read `discontinuada = False` and
  `valores_cant = 29`, covering 1997–2025. Fetching it returns an empty
  array. The flag is not merely absent, it is wrong; the count is not
  merely missing, it is contradicted. The monthly equivalents (`142.3_*`)
  are fine, and the fetcher uses those.
- **The export rubros are half-dead.** The MOI (manufactures of industrial
  origin) export IDs serve empty at every frequency, so MOI here is
  computed as the residual of total exports minus the other three rubros.
  That is exact by the ICA's own definition, but it is a reconstruction and
  the code says so.
- **`collapse=year` silently drops partial years.** Ask the API to
  aggregate a monthly series annually and the current, incomplete year
  disappears from the response entirely. Not as a null — it is simply not
  there. This deleted 2026 from every monthly series in the first version
  of the fetcher. The fix was to stop using server-side collapse and
  aggregate locally, which also means the code knows how many periods it
  summed and can mark a year partial instead of reporting ten months as a
  year.

- **A dead rate keeps publishing a zero.** `174.1_T_INTERS_0_0_56`, the
  5-to-10-year mortgage rate, has its last real reading in June 2017 and
  then serves a clean `0.0` every month for 106 further months, through
  2026. The overdraft rate (`174.1_T_INTERO_II_0_0_57`) does the same from
  December 2016, for 112 months. Nothing in the payload distinguishes that
  from a rate that fell to zero; only knowing that no Argentine mortgage
  has ever been free does. `drop_zeros()` exists for this and prints where
  each series really ended.
- **A series can have a 42-year hole in the middle.** Loans to the private
  sector (`174.1_PTAMOS_TAL_0_0_33`) runs from 1940 to 2026 and is empty
  from July 1975 to March 2017. The obvious substitute, "préstamos
  totales", includes the public sector and other financial institutions —
  in December 2017 the private share was 42% of it — and the
  public-sector series you would subtract is null across the whole window.
  The credit panel is built from the BCRA's own API instead; see §6.
- **The dating convention is per series, not per API.** The monthly IPC is
  dated at the start of its month and the quarterly Gini at the start of
  its quarter, but the half-yearly poverty series is dated at the day
  *after* the half it describes ends. §5 has the details; it is the
  single most expensive thing in this file to have discovered late.

### The worst bug I wrote, and why it belongs in this file

The first fetcher inferred each series' frequency from its ID, because the
IDs mostly encode it: `_M_` monthly, `_A_` annual, `_T_` quarterly. Mostly.
The primary fiscal result from 2017 onward is `379.9_SUPERAVIT_017__23_94`
— monthly, with no marker at all. The sniffer read it as annual, took the
December reading as the whole year, and reported **2024's +1.78% of GDP
primary surplus as a −0.22% deficit**. The sign was wrong on the single
most politically loaded number in the atlas.

Frequency is now a declared field in every series definition, never
inferred, and `fetch_datos_gob.py` carries a comment saying why. The
general lesson: when a naming convention is 95% reliable, the 5% will be
the series someone argues about.

---

## 2. The INDEC gap (2007–2016), and what to do about it

In January 2007 the national statistics institute was intervened. The
consumer price index it published from then until late 2016 is not a
measurement of Argentine prices, and in 2016 the incoming administration
declared a *statistical emergency* and withdrew the series rather than
defend it. Poverty figures from the same period are withdrawn too — there
are years with no official poverty number at all, because the agency simply
stopped publishing rather than publish something indefensible.

This is not a data-quality caveat to put in a footnote. It is a ten-year
hole in the middle of a twenty-year atlas, and it sits exactly where the
story is.

How this repository handles it:

- `events.INDEC_GAP = (2007.0, 2016.9)` is shared by every plate. Charts
  **band** the gap rather than draw through it. A line that crosses 2007
  without acknowledging it is lying by omission.
- For inflation the substitute is **IPC San Luis** — the San Luis
  provincial statistics office, which kept measuring through the
  intervention and is official, just not national. The validation that made
  me willing to use it: for 2017–2022, where both exist, San Luis and the
  new national INDEC agree closely (national 25.0, 47.1, 53.8, 36.1, 50.9,
  94.8). A substitute that tracks the real series where they overlap is a
  substitute worth splicing; one that does not is a guess.
- The two are **never drawn in the same colour**. `style.ASTERISK` exists
  for exactly this: a series that is official but not comparable with the
  one beside it. The eye should register "different kind of number" before
  the reader gets to the legend.

The alternative — using the intervened official series because it is
"official" — would make the charts worse, not more rigorous. Fidelity to a
source that the source's own owner has disavowed is not fidelity.

---

## 3. Nominal pesos are not a unit

Over this window Argentine prices rose roughly **1,200-fold**. A peso
figure from 2008 and a peso figure from 2025 are not two values of one
variable; they are two different variables that share a currency symbol.

Nothing in this atlas is plotted in nominal pesos across years. Everything
comparable is in US dollars, as a share of GDP, or deflated. `style.fmt_ars`
exists and is documented as valid *only beside its own year* — it labels a
single bar, never an axis.

The same logic forced the fiscal panel's shape. The primary result comes
off the API in pesos of the year, which is useless as a series, so it is
divided by nominal GDP. 2026 is blank there: the monthly fiscal data
exists, but no annual GDP figure does yet, and inventing a denominator to
avoid an empty cell is how a chart starts lying.

### And there is more than one dollar

For most of 2011–2015 and 2019–2023 the official exchange rate was a price
at which most Argentines could not actually buy dollars. Charting the
official rate alone through a *cepo* describes a market that was not open.
The gap between official and parallel is not noise around the real rate —
during those years the gap **is** the story, so the plate draws both.

This is also the one place where the atlas leaves official sources
entirely, and it says so loudly. The blue dollar is by construction a rate
the state does not publish; the CCL is implied by arbitraging a
cross-listed bond; country risk is J.P. Morgan's EMBI+, a vendor index. All
three come from Ámbito Financiero's daily series via a community mirror.
The Merval and the S&P 500 are from Yahoo because BYMA publishes no open
historical endpoint for its own index. `fetch_markets.py` opens with a
paragraph stating that these are the only unofficial series here, and
`SOURCES.yaml` marks them as market references rather than attributing them
to an institution that never published them.

---

## 4. Three fiscal methodologies, one axis

The non-financial public sector result exists as three series —
1993–2006, 2007–2014, 2015 onward — and they are not continuations of each
other. The treatment of central-bank transfers and ANSES income changes
across the breaks, in ways that move the headline number by more than the
deficit does in a normal year.

They are plotted as three segments with visible joins, not as one line. A
reader who wants the long arc can still see it; a reader who wants to know
whether 2014 and 2016 are comparable can see that they are not.

---

## 5. The poverty series is dated six months wrong

This one cost the most and shows the least. INDEC's half-yearly poverty
rate comes off the gateway dated at **the day after the half it describes
ends**: `2024-07-01` is the *first* half of 2024, and `2025-01-01` is the
second. Read the dates the way they are written and the whole series
shifts six months.

What that does in practice: the 52.9% peak is the first half of 2024, the
half immediately after the December 2023 devaluation, against 41.7% in the
half before it and 38.1% in the half after. Taking the "last reading of
2024" gives you 52.9% labelled as the *second* half — the wrong half of a
V-shaped move, which turns a sharp spike-and-recovery into a rise that
never came back.

The infuriating part is that this is not the gateway's convention. In the
same API:

| series | dating |
|---|---|
| monthly IPC | start of period — `2016-12-01` = December 2016 = 100.0 |
| quarterly Gini | start of period — `2024-01-01` = 0.467, the post-devaluation Q1 |
| half-yearly poverty | **end of period** — `2024-07-01` = H1 2024 |

The Gini and the poverty rate come from the *same survey* and are published
in the *same report*. One is offset and the other is not, and no metadata
field distinguishes them. The only way to find it is to know what a
published number should be and notice it is in the wrong cell.

So: `semesters()` re-dates poverty explicitly and says why in its
docstring, and both halves are written out as separate columns rather than
collapsed, because INDEC quotes them separately and because the gap
between them is sometimes the entire story.

The general rule I would now give anyone using this API: **verify the
dating convention of every series against one externally known value
before you plot it.** Not per API, not per publisher, not per dataset —
per series.

---

## 6. Credit, household debt and rates: going in a second door

The series gateway could not supply this panel (see §1: a 42-year hole in
private credit, two rate series that publish zeros for a decade). The
BCRA's own `api.bcra.gob.ar/estadisticas/v4.0` supplies all of it, and
supplies it better: private credit daily from 1996, the deposit rate from
1990, credit-card balances from 2002, the overdraft rate from 2009, the
personal-loan rate from 2010. Same institution, same numbers, different
door. It is worth saying that the first-party API beat the central
catalogue here, because the usual advice is the opposite.

Decisions inside that panel:

- **A year is its December average, not 31 December.** The last business
  day of an Argentine December is a liquidity spike. Averaging the month
  smooths it without reaching back into a different price level, which an
  annual average would do in a year where prices tripled.
- **Household debt is the four retail lines** — credit cards, personal
  loans, mortgages, pledge loans — not total private credit. Business
  lending is excluded deliberately; the question "how indebted are
  households" is not answered by a number containing corporate overdrafts.
- **Every rate is published nominal and real.** The nominal rate on its
  own carries almost no information here: 95.9% on a time deposit in 2023
  was a 37% real loss. The real rate is computed Fisher-exact against the
  national IPC, and only for the years that index covers.

Three things the data says that I did not expect to be so stark:

1. **Argentine credit is tiny and always has been.** Private credit ranges
   from 9.0% of GDP (2022) to 14.7% (2017) across the whole window,
   against 50-70% in Chile or Brazil. The 2024-25 expansion that was
   reported as a boom takes it from 10.5% to 13.5% — enormous in relative
   terms, and still a banking system that barely lends. Any chart of this
   needs to say so, or a reader will scale an Argentine boom against a
   Chilean baseline and misread it completely.
2. **Mortgage lending effectively ceased.** 1.56% of GDP in 2007-08,
   **0.28% in 2024** — a 15-year disappearance of home finance, recovering
   only to 0.74% in 2025. It is the single clearest line in the whole
   atlas and nobody puts it on a chart.
3. **Saving was punished every year from 2017 to 2024.** The real deposit
   rate is negative in all eight: −4.9, −10.9, −4.3, −4.7, −11.0, −21.3,
   −37.1, −29.4. It turns positive in 2025 (+2.2) — at which point
   borrowing becomes brutally expensive in real terms instead (+32.0% real
   on a personal loan), and the non-performing ratio on private loans
   jumps from 1.54% to **5.54%**, its worst reading since 2006. The credit
   expansion and the delinquency spike are the same event seen a year
   apart, and the panel should draw them together.

The two system-level indicators behind that last point — non-performing
loans and credit as a share of bank assets — do come from the series
gateway (dataset 332), where they are published as percentages while the
catalogue declares their unit to be "En millones de pesos". The numbers
are right and the label is wrong, which is the least harmful version of
this problem but still one you have to catch.

---

## 7. Health and vital statistics: the best-organised data here

DEIS (Dirección de Estadísticas e Información de Salud) publishes
microdata-shaped CSVs — one row per (year, jurisdiction, cause, sex, age
group) with a count — and summing the count column reproduces the published
national totals **exactly**. That is a rarer property than it sounds, and
it means the fetchers can assert it. `fetch_deis.py` and `fetch_causes.py`
both hard-code known published totals and refuse to run if the sum
disagrees; a silent upstream reshape would otherwise quietly rewrite
history in a committed CSV.

Rough edges, all cosmetic: the 2005–2022 deaths file is 100 MB (streamed,
never loaded), the births equivalent is 68 MB, and the per-year files
switched from comma- to semicolon-delimited in 2023 with no announcement
and no change to the extension.

### COVID-19 and influenza (2020–2024)

Both come out of the same cause-of-death files, which makes them directly
comparable — the point of putting them side by side. Two things a reader
needs:

- **The cause column is truncated to three characters.** U07.1
  (laboratory-confirmed) and U07.2 (clinically diagnosed, untested) cannot
  be separated. The COVID series here is confirmed *and* probable.
- **It does not match the pandemic dashboard, and should not.** The
  ministry's epidemiological dashboard counted confirmed cases and reported
  roughly 130,000 deaths through 2022; this registry records **161,767**
  for 2020–2022 and 164,785 in all. The registry is the wider count and the
  later one. It is not a correction of the dashboard — the two were
  answering different questions — but the 30,000-death gap between a
  country's two official COVID numbers is worth stating rather than
  quietly picking a side.

**Influenza is effectively not coded in Argentina.** The J09–J11 column runs
from 9 to 358 deaths a year against 15,000–40,000 pneumonias, because a
fatal influenza is ordinarily certified as the pneumonia it became. Quoting
the influenza column alone would produce a true-looking and completely
false comparison with COVID. The CSV therefore carries a `respiratory`
column (influenza + pneumonia) and the fetcher's docstring says no panel
should use the flu column on its own.

Two things in that series are real and not artefacts, and both are worth a
chart annotation: the **2009 influenza spike** (358 deaths, H1N1 — the only
year the flu code means anything) and the **2020 pneumonia drop** (32,451 →
27,472) during the hardest lockdown, which recovers to a new high of 40,483
by 2024.

### The birth collapse

Plate 08 was going to be a population-ageing panel until the projections
turned out to stop at 2040, with no peak inside the window. The honest
story was sitting in the births file anyway, and it is a bigger one:
**777,012 births in 2014, 413,135 in 2024 — down 46.8% in ten years**, with
natural growth falling from 451,473 to 36,730. Argentina is within a few
years of recording more deaths than births. I have not found another
country in the region that halved its births that fast.

---

## 8. Femicides: a complete rate, an incomplete count

The Corte Suprema's Registro Nacional de Femicidios publishes a continuous
**rate** series from 2014, but the **counts** are scattered across annual
reports and only some years are machine-readable (2017, 2019, 2022, 2023,
2024, 2025). The rate line is therefore published complete and the count
cells are left blank where the number is not known, rather than
interpolated.

Three design mistakes were flagged from the Brazilian edition of this atlas
and are avoided here deliberately:

1. A red "of which femicides" line drawn against a black total must *say*
   it is a subset of the black line. Proximity does not communicate
   containment.
2. A title that promises a share must draw the share. If the panel plots
   two counts, the title says two counts.
3. The caveat explaining why a line rises must sit **next to the line**.
   A classification artefact explained in the far corner of the figure is
   an artefact the reader will not connect to anything.

---

## 9. Still unresolved

- **Public debt as a share of GDP, from an Argentine publisher.** It is
  still not on `apis.datos.gob.ar`: the only debt-to-GDP series in the
  catalogue, `313.1_EN_PORCENTPIB_0_T_21`, is *private* external debt and
  stops in 2017, and the `451.*_SERVICPIB_*` series are debt **service**,
  not stock. The Secretaría de Finanzas publishes quarterly figures as PDF
  tables. The fiscal plate now draws the IMF's general-government gross
  debt (WEO `GGXWDG_NGDP`, which the IMF datamapper serves to a browser-
  shaped request), labelled as the IMF's. A national stock in a machine-
  readable form is still the gap.
- **A policy rate before December 2015.** It does not exist: see §11.
- **A peso 10-year benchmark.** It does not exist either: see §11.
- **Pre-2012 Corruption Perceptions scores.** TI scored Argentina on a
  0-10 scale with a different method until 2011 and says the two are not
  comparable; no machine-readable file of them was reachable, so the world
  plate starts in 2012 and says so.

---

## 10. What would make this easier

Nothing here is a complaint about effort; the Argentine open-data team has
clearly done serious work. These are the things that cost the most time:

1. **Make `serie_discontinuada` true.** The field already exists, which
   is the frustrating part. A series the API serves empty should not be
   advertised as live with a value count of 29. Right now the only way to
   know is to fetch it.
2. **Let partial years through.** `collapse=year` dropping the current year
   is a defensible default and an undocumented one. A `partial: true` flag
   on the period would be strictly better than silence.
3. **Publish the fiscal methodology breaks as data.** Everyone who uses the
   SPNF series rediscovers the three-methodology problem independently, by
   getting it wrong first.
4. **Put the debt ratio in the series API.** See above.
5. **Keep the delimiter.** Changing a published CSV from commas to
   semicolons between editions, under the same `.csv` extension, breaks
   every downstream reader silently.
6. **Declare the dating convention per series.** One field — does this
   date label the start or the end of its period — would have saved more
   time than everything else on this list combined. See §5.
7. **Serve `null`, not `0.0`, for a rate that is no longer measured.** A
   mortgage rate of zero published monthly for nine years is worse than
   no mortgage rate at all, because it is plottable.

The underlying discipline this repository tries to keep: *committed CSVs
are the source of truth, charts are a build artefact, and every number can
be traced to the fetch that produced it.* Where a source is broken or
withdrawn, the chart says so on the panel. Where a series had to be
reconstructed, the code that reconstructed it says how. That is cheaper
than it sounds and it is the only reason the primary-surplus sign error
above was caught at all.

---

## 11. The plate spine (2026-10-22)

Every plate now keeps to the shared spine (`PLATE_SPINE.md`): the same
indicator in the same slot, unit and scale as every other country, so the
comparison viewer can wipe one country's plate over another's. What that
changed here, and why.

### Chapters and topics

The nine chapter ids are kept so links survive, but three of them answer a
topic their name does not suggest: **03-living → people**, **08-people →
demography**, **04-state → fiscal**. Three chapters are new:
**10-spending**, **11-world** and **12-mortality** (the cause-of-death
panels moved there from demography). **02-prices** stays as Argentina's
own lens — inflation, the two dollars, the gap, reserves — and its CPI,
currency and reserves also meet everyone else on economy slot 3, markets
slot 3 and world slot 4.

### Rates, and the populations under them

Rule 5: a rate is a count over the population of the same year and scope.

| rate | count | population | note |
|---|---|---|---|
| births, deaths, natural increase per 1,000 | DEIS `social/vitals.csv` (registered, by residence) | INDEC `macro/gdp.csv : population_mn`, national, mid-year projection | 2014 births: 777,012 ÷ 42.67 m × 1,000 = 18.2 |
| crude death rate per 1,000 | DEIS `social/causes.csv : deaths_total` | same | identical totals to vitals.csv |
| COVID-19, pneumonia, influenza per 100,000 | DEIS `social/causes.csv` | same | 2021 COVID: 84,695 ÷ 45.81 m × 1e5 = 184.9 |
| suicide per 100,000 | DEIS X60-X84 | same | crude; WHO's line beside it is age-standardised |
| land-transport deaths per 100,000 | DEIS V01-V89 | same | wider than road traffic (see below) |
| homicide per 100,000 | — | — | SNIC's **published** rate, drawn as published; SNIC divides by the same INDEC projection |
| femicide per 100,000 women | — | — | the CSJN's **published** rate |
| net migration per 1,000 | WB `SM.POP.NETM` (a count) | WB `SP.POP.TOTL`, mid-year | same source both sides |

INDEC's projection and the UN's WPP disagree by about 1.3% in 2024 (46.30 m
against 45.70 m). Rates here use INDEC's, because it is the denominator the
Argentine registries use themselves; the demography plate draws both
populations so the difference is visible.

The cause columns `suicide` and `transport` are new in `causes.csv`,
added by `fetch_causes.py` from the same DEIS files, with the published
totals re-verified. The file's cause code is truncated to three
characters, so **V01-V89 cannot be narrowed to road traffic** (WHO's
definition needs the fourth). It is labelled "all land transport", and it
still comes out far *below* WHO's road estimate — 5.2 per 100,000 in 2020
against WHO's 13-15 — because the register codes many crash deaths as
events of undetermined intent, which WHO models back in. The plate says
the two do not measure alike rather than choosing one.

### Other conversions

- **Gini** is INDEC's 0-1 coefficient × 100, to share the 0-100 axis.
- **Poverty, slot 2**, is the mean of INDEC's two halves, only where both
  exist: 2026 has one half and is not drawn as a year. The halves
  themselves are the lens panel, plotted at Y+0.25 and Y+0.75.
- **The peso** is `fx_index` of the official annual-average rate: 3.07 per
  dollar in 2006 = 100, 1,244.5 in 2025 = 0.25. The log axis grows two
  decades below the reference range to hold it, and says so.
- **Merval in US$** is the year-end close over the official year-end rate,
  indexed to 2006; under the cepos the CCL would give a lower dollar value,
  and is staged (`parallel_fx.csv : ccl`, from 2013 only).
- **Interest paid** is the IMF's primary balance minus its overall balance:
  net interest. The overall balance is published to one decimal, so the
  difference carries ±0.05 points of rounding. The national budget's broader
  debt-service function (`spending_by_function.csv : deuda`) is not drawn in
  the canonical interest slot because it is not a comparable interest-only
  series.
- **Spending by function** maps the thirteen national functions onto the
  spine's seven groups: social protection = previsión + asistencia +
  asignaciones; health = the three salud lines; education = básica +
  superior; general public services = funcionamiento + deuda (COFOG puts
  interest there); economic affairs = energía + transporte; defence and
  public order = defensa y seguridad; **other** = the published total less
  the thirteen (0.1 to 1.8 points). It is the **national government only**,
  not general government: the provinces run schools and hospitals, which
  is why education reads under 1% of GDP.
- **Public investment** is the national public sector's "inversión real
  directa" (Esquema AIF) over nominal GDP, in its three methodologies,
  never joined. No harmonised government-GFCF series exists for Argentina.
- **The trade balance** in slot 2 is World Bank exports minus imports of
  goods and services, the same definition as slot 1. INDEC's customs-goods
  balance is kept as a dollar annotation; 2026's year-to-date surplus has no
  annual GDP denominator and is stated in a note rather than overlaid.
- **Government bond yield.** Argentina has no peso 10-year benchmark. The
  sovereign's long debt is in dollars, so slot 2 draws the US 10-year
  Treasury (annual average of the Treasury's daily par yield) plus the
  EMBI+ Argentina spread (annual average): the yield the market asked of
  Argentine dollar debt, labelled as that sum. The EMBI+ basket is not
  exactly ten years' duration.

### The policy rate (rule 11, "genuinely absent")

The BCRA's own series of monetary-policy rates (API variable 160) begins
on 16 December 2015 and ends on 10 July 2025, when the BCRA stopped
setting one and moved to steering monetary aggregates. Before 2016 there
was no single announced policy rate — the BCRA steered through LEBAC
auctions at many tenors and through its repo corridor — so a policy-rate
line for 2006-2015 would be invented. The markets and credit plates draw
the policy rate's annual average for the nine whole years it existed
(2016-2024), and say on the panel that none existed before or after.

BADLAR (variable 7, private banks' rate on 30-day deposits above a
million pesos) is drawn across the whole window as a **labelled proxy**,
never as the policy rate. The justification: it was the reference rate of
the BCRA's own BADLAR-indexed NOBAC notes (variables 191 and 194 are their
margins over it), and it tracks the policy rate closely where both exist
(2023: 95.8% against 100.0%).

### Marks

- **Recession bands** are every calendar year INDEC's real GDP fell —
  2009, 2012, 2014, 2016, 2018-20, 2023-24 — drawn behind every time series
  and named once per plate in the slot-1 legend. `tests/test_plates.py`
  checks the list against `gdp.csv`.
- **The INDEC intervention** is a hatched band from 2006.5 to 2016.5 (the
  annual readings 2007-2016) behind every series INDEC produced or that is
  built on its national accounts or CPI — which includes the IMF's and the
  World Bank's republications of them.
- **The running year.** 2026 is year to date everywhere it appears: CPI is
  the rise since December, trade the months published, reserves and the
  exchange rate the latest reading. It is dashed on a line and hatched on a
  bar. Before the spine, 2026 was drawn as a full year in GDP, CPI and
  trade; the headline inflation figure on the page now stops at 2025.

### Stories moved rather than dropped

- Dollar GDP and its peak move to world slot 1; GDP per person stays in
  economy at the World Bank's figure, with INDEC's own beside it: the two
  agree within 2% except in 2012-2015, when INDEC's is 7-12% higher.
- The real-output index (2006 = 100) is gone: the growth bars carry the
  same information on the shared axis, and the slot note says how many
  years fell.
- The homicide count and the femicide counts move into notes: a count
  cannot share an axis with a rate, and the three-year femicide panel
  could not sit on the shared time axis.
- The reserves-against-risk twin axis is gone: reserves are on the world
  and prices plates, and country risk is the gap between the two lines of
  the bond-yield panel.
- The mortgage collapse (1.56% of GDP in 2007, 0.28% in 2024) is a note on
  household debt; the real interest rates are the credit lens.
- Influenza deaths are drawn, per 100,000, beside pneumonia in the
  mortality lens, so the reader sees how little the code is used rather
  than being told.
# Migration

The gross-flow slot is deliberately pending. DNM entry and exit totals count
border movements (trips), while residence grants count administrative
decisions; neither is a resident immigration/emigration pair. Net migration is
the existing UN WPP modelled count divided by the same WDI population. Stock
uses INDEC's published census share of private-dwelling residents born abroad,
and the lens uses 2022 census countries of birth. Birthplace is never relabelled
as citizenship.
