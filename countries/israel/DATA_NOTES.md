# Israel — data notes (Phase B)

Everything the plates assert about definitions, seams and conversions, in
one place. SOURCES.yaml remains the publisher-level record; this is the
plate-level one.

## The RTL font gate (recorded, not worked around)

Israel is the atlas's first Hebrew country. `core.style.SCRIPT_FONTS` has
no `he` entry (it has only `ko`), so `has_script_font("he")` returns True
by its own rule — "a language with no script-font entry can be rendered by
the Latin fallback" — and the layout probe runs for `israel/he`; it is
**not** skipped. The fallback chain is DejaVu Sans, which carries real
Hebrew glyphs (no tofu) but does **no bidi reordering**: an Hebrew string
drawn by matplotlib appears left-to-right in logical order. That is a core
RTL gap (Phase C page work), not something this lane may fake: no
hand-mirroring, no reversed strings, no manual RLM tricks in plates.py.
Consequences held here:

- the he plates render with the same LTR geometry as every other locale
  and must reach **zero** layout faults like en and pt;
- `core.style.SCRIPT_FONTS` gaining a `he` entry (and the site's AFFIX /
  CURRENCY_AFFIX carrying he) are core needs to report, not to build;
- the ILS is written `ILS` in plate text, never the U+20AA sign, so no
  plate depends on a currency glyph.

## Bands: COVID-2020 only, verified against the staged vintage

country.yaml carries one band: `{from: 2020.0, to: 2020.9, label:
"COVID-19"}`. Decision record, all pinned in tests/test_plates.py:

- 2020: `macro/gdp_growth_from_imf.csv` (the staged WEO vintage) says
  **-1.9%** — a real annual contraction. The two-quarter q/q test that
  would normally corroborate it rides on CBS quarterly, which is parked;
  every country built from the harmonised layer draws the annual sign,
  this one included.
- 2008-09: **no band.** The discovery pass's "−2.8 in 2009" was Sudan's
  row (the DataMapper `/ISR` segment does not filter — see SOURCES.yaml).
  The staged series says +3.2 (2008) and +1.2 (2009), and the World Bank
  national-accounts vintage independently agrees. A contraction the
  staged vintage does not show is not bandable.
- 2023-25 war years: **no band.** +2.0 / +1.7 / +3.5 — annual growth
  stayed positive. CBS quarterly might yet meet the two-quarter rule for
  the war quarter; until it returns, the war is drawn as events.

## Events, not bands (events.py)

- 7 October 2023 (mark at 2023.75) on the economy, fiscal and security
  panels, where the data visibly turn.
- The war-fiscal reaction — revenue 34.6% of GDP vs expenditure 43.7% in
  2024, balance −8.1%, debt 61.9 → 67.7 → 67.9% of GDP — is annotated on
  the fiscal plate as events and notes. It is never turned into a band,
  because a band would assert a growth contraction the series denies.
- The October-7 files inside the police murder count (2023: 1,209 type-301
  files) are annotated on the security plate as recorded data. Police
  commentary sometimes excludes the national-terror files from "murder
  for the year"; **the file does not** — that definitional seam is stated
  on the panel.

## Count→rate conversions (spine rule 5) and the population used

All rates use the World Bank `SP.POP.TOTL` mid-year series staged as
`demography/demography_from_wb.csv` — same year, national scope, matching
the UNODC/WHO rate series' own denominator when a published rate exists
(where a publisher publishes a rate, the published rate is drawn, not a
recomputed one):

- police murders per 100,000: `security/homicide_police_from_datagovil.csv`
  murder_301 ÷ that year's population × 100,000. Spot: 2023 =
  1,209 / 9,849,000 = **12.28** per 100,000 (test recomputes).
- olim per 1,000: olim_flow ÷ population × 1,000. Spot: 2022 = 76,601 /
  9,557,500 = **8.01** per 1,000.
- net migration per 1,000: WB `SM.POP.NETM` ÷ population. Spot: 2022 =
  50,004 / 9,557,500 = **5.23**.
- permits per 1,000: PIBA new-permit counts ÷ population (flow wording
  throughout — a permit is a record, not a person, and never a stock).

## Seams that are drawn as seams, never spliced

- **Homicide, security slot 1:** the UNODC rate (via WB, 2005-2022) and
  the Israel Police type-301 count converted per 100,000 (2021-2025) are
  **two labelled series on two colours**. The police window is 2021+
  only — it is stated on the panel and pinned in tests; nothing is
  extrapolated backwards into the 2006-2020 half, and the UNODC rate is
  never extended past 2022 to dress up the line. CBS death-certificate
  homicide (the residence-based second count) is parked with CBS.
  Type 302 (killing by hostile action) is its own column and its own
  note, never added to 301.
- **Aliyah vs permits vs net migration (migration plate):** olim are a
  Law-of-Return legal flow (Ministry of Aliyah and Integration, 2015+);
  PIBA issuance is permit records (2019+); UN net migration is an
  estimate. Three objects, three panels/series, one rule: never summed
  into one "immigration" line. The PIBA lens excludes the tourist/visitor
  classes (ב/2 family dominate the raw totals), excludes the diplomatic
  and unverified-definition classes, and excludes the PIBA classes named
  עולה/חוזר because they would double-count the olim panel; which classes
  are in is stated on the panel and computed from the CSV in tests.
- **FX:** the WB `PA.NUS.FCRF` annual averages (2005-2025) carry the
  index line. The Bank of Israel PublicApi row is a **snapshot of the
  representative rate on one intraday timestamp** (2026-10-22), quoted as
  a labelled snapshot note — never appended to the history line. BoI
  daily history is dead (404); that is why the line is WB's.
- **Equities:** TA-125 via Yahoo (`official: false`). Yahoo's levels
  differ from TASE's published year-end closes by a few percent (SOURCES
  records the pairs); the panel says the source is a redistributor. The
  US$ conversion uses the staged WB FX — pinned spot: 2006 base =
  925.60/4.4558, 2025 = 3,654.94/3.4519 → index ≈ 510 against the S&P
  500's ≈ 483. 2026 is not converted (no staged 2026 FX) and the partial
  year stays hatched/dashed.

## Harmonised lines with the national line named (CBS pattern)

CBS is the publisher of record and unreachable from this machine
(SOURCES.yaml meta.pending), so — exactly the Canada pre-StatCan pattern —
economy, trade, people-shaped, demography and security slots ride the
WB/IMF/OECD layer, each footered **"the CBS national line when CBS
returns"**. The OECD `DSD_LFS@DF_IALFS_INDIC` unemployment line IS
Israel's own LFS re-published by the OECD, so it is labelled as the LFS
definition (survey, not the NII payroll register); the ILO-modelled WB
line is the beside-line.

## Pending slots (ctx.pending) and skipped chapters

Claimed and pending, each with its reason on the panel:
fiscal.interest (IMF GGXWDINT not staged this pass — report, fetchable),
trade.destinations (customs/Comtrade not staged), markets.policy_rate and
markets.bond_10y (BoI beyond FX parked), world.cpi (Transparency
International not staged), migration.foreign_born (UN DESA migrant stock
not staged).
No chapters are drawn for **spending** (no COFOG staged), **people** (no
Gini/poverty/minimum wage staged — OECD IDD version unresolved, WB Gini
definition unverified), **credit** (BIS answers "No results for query"
for IL; BoI side parked) and **mortality** (CBS-only). A chapter of six
pending panels is worse than no chapter; the slots and routes are named
in SOURCES.yaml meta.pending.

## Other honesty notes carried on the plates

- olim 2006-2014: not on the portal (XLS behind a CloudFront wall); the
  flow panel opens in 2015 and says so — no back-fill.
- WB suicide series stops 2021 and road deaths 2019 in WB's own coverage
  — the lines stop; the holes stay holes.
- Fertility/crude birth/death for 2025 are blank in the WB vintage — the
  lines stop at 2024.
- population index 2025 ≈ 143 vs the 80-130 reference: the axis **grows**
  and carries the "scale extended" marker (spine rule 6), never the data.
- WB reserves 2024 (214.5bn) run 1.2% above the BoI's own release (adds
  IMF-related items) — footered, not reconciled by hand.
- HDI is one vintage (HDR 2025, series to 2023) throughout.
