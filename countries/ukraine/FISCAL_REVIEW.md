# Ukraine Treasury fiscal contribution — reviewer handoff

Status: **verified complementary national Treasury cash-budget source**, not a
replacement for the existing canonical fiscal chapter. The current upstream
Ukraine edition publishes **nine plates, including IMF WEO general-government
fiscal statistics**; this adds a separate publisher-defined national dataset. Do not merge the older
`feat/ukraine-atlas` branch or alter shared comparison scales.

## Why this source and what it measures

The computing institution is the **State Treasury Service of Ukraine**.
The National Bank of Ukraine republishes the Treasury cash-budget execution
cube at:

```
https://bank.gov.ua/NBUStatService/v1/statdirectory/budget?json
```

The committed `data/fiscal/treasury_functional.csv` retains **2011–2025**,
one row for each *calendar-year execution* and the original ten national
functional categories plus the Treasury functional total. Dimensions:

| Cube field | Accepted value | Why |
|---|---|---|
| `freq` | `Y` | Annual observation, never monthly or YTD |
| `mcr200p` | `CBU` | Consolidated budget, never `SBU` state budget |
| `tzep` | `F_M_VC` | Nominal million UAH, not % GDP |
| `id_api` | `gf_budgtef_0100`…`1000` | Ten direct national functional groups |
| `id_api` | `gf_budgtef_Total_1` | Total **less interbudget transfers** |
| `leveli`/`parent` | 2/`budgtef_Total_1` for groups; 1/`budgtef_Total_2` for total | Guards against hierarchy revisions |
| `dt` | `YYYY0101` | **January 1 stamps the prior year**: 20240101 = 2023 outturn |

The original research script had misread the last dimension and attributed
2023 values to 2024. It is **not** reused in this contribution.

The ten functional amounts sum to `Total_1` within 0.3 **million** UAH for
each of the 15 complete years (single-decimal source rounding). No interpolation,
splicing, annualization, currency conversion or inflation adjustment is used.

The data are **Treasury consolidated-budget cash execution**, not IMF GFS
general-government accrual expenditure, balance, debt or a validated COFOG
classification. These are substantively different fiscal perimeters, not
alternative labels for the same measurements. Consequently, the CSV is
**not read by any canonical fiscal/spending plate** and the trilingual
`treasury_preview.py` is an **offline supplementary review visualization**.

## Independent source-year and value anchors

Ministry of Finance, *Budget of Ukraine 2024*, functional expenditure tables
(section 2.3, pages 34–37):
https://mof.gov.ua/storage/files/Badgef%20of%20Ukraine2024.pdf

| Calendar year | Defence, million UAH | Functional total, million UAH |
|---|---:|---:|
| 2022 | 1,143,163.6 | 3,043,871.4 |
| 2023 | 2,097,621.9 | 4,441,364.6 |
| 2024 | 2,305,242.7 | 4,945,680.7 |

The last two years are pinned in `fetch/fetch_treasury.py` as exact
publisher-revision anchors. **Do not move those anchors forward one year.**

### Annual 2025 independently confirmed; earlier December edition revised

The Ministry of Finance's official **2025 annual consolidated-budget**
workbook (sheet `2025 рік`) is at:
https://www.mof.gov.ua/storage/files/4_%D0%97%D0%91_%D1%80%D1%96%D0%BA_%D1%81%D0%B0%D0%B9%D1%82_25.xlsx

Primary-workbook byte provenance (retrieved directly from the Ministry
in [this read-only GitHub Actions run](https://github.com/glaucojrcarvalho/worldreports/actions/runs/40145936696)):

- Annual 2025 XLSX: **144,827 bytes**, SHA-256
  `0cf48ddcf1b042c548ff735d6bf6105da3cfdec1c86d8e2e40fde70b99b6cc1c`.
- December 2025 XLSX: **144,721 bytes**, SHA-256
  `989de22f0a61ef5bee36def79b8db79aa59b88e00dddea67d7f7cbfd58d122f6`.

The full binaries are review artifacts, not chart inputs or committed
repository data. The review-only normalized values and source URLs
are in `fetch/reference_mof_2025_annual.csv` and
`fetch/reference_openbudget_2025.csv`.

| Official edition | Total, million UAH | Economic affairs, million UAH |
|---|---:|---:|
| MoF December 2025 | 5,999,467.11164619 | 258,106.09460700 |
| MoF annual 2025 | 6,006,387.27484437 | 264,998.32655720 |
| NBU annual 2025 (rounded) | 6,006,387.3 | 264,998.3 |

**All 10 functional groups and the total in the MoF annual edition
agree with NBU within 0.05 million UAH**, the NBU's reporting
precision. MoF publishes group `0100` as two lines (general public
services excluding debt payments + debt service). The two parts sum to
512,192.25565216 million UAH and reconcile to the NBU's 512,192.3.

The portal's [earlier December edition](https://openbudget.gov.ua/?budgetType=CONSOLIDATED&month=12&year=2025)
is **6,920.16319818 million UAH below the later annual edition**.
Most of that change (**6,892.23195020 million UAH**) is in
`0400` economic affairs. It is not a rounding problem, but a
**cross-publication revision**. The precise administrative
transactions responsible for the revision are not verified; we make
no claim about their cause. The December snapshot is preserved as
`fetch/reference_openbudget_2025.csv`; the later MoF source is
`fetch/reference_mof_2025_annual.csv`. The reference CSVs and
`fetch/audit_open_budget.py` compare both editions without replacing
any curated data. The three-language national preview discloses this
difference, not a supposed unresolved same-vintage discrepancy.

## Reproduction and fail-closed gates

The renderer uses **committed CSV only**. Fetchers cannot write to
`data/`. The NBU fetcher checks HTTP status, JSON MIME and encoding,
record schema, code lists, parent/level hierarchy, currency unit,
reporting dates, duplicates, gaps, numeric sanity, annual identities
and independent publication anchors.

To stage, *without promoting* source data:

```sh
python3 countries/ukraine/fetch/fetch_treasury.py
python3 countries/ukraine/fetch/audit_open_budget.py
```

The read-only live fetch comparison was executed from the contributor's
**research branch** `feat/ukraine-fiscal`. It re-fetched the complete NBU
budget cube, validated every historical year and found the staged
sidecar **byte-identical** to the committed 2011–2025 CSV (matching
SHA-256). [Verified run](https://github.com/glaucojrcarvalho/worldreports/actions/runs/40143540040).
This source-first PR deliberately **does not introduce research-only
GitHub Actions workflows** into the maintainer's repository.

Offline checks and trilingual review artifacts:

```sh
python3 -m pytest countries/ukraine/tests/test_treasury.py countries/ukraine/tests/test_treasury_reconciliation.py -q
python3 -m pytest countries/ukraine/tests/test_plates.py tests/test_spine.py -q
python3 countries/ukraine/treasury_preview.py --output /tmp/ukraine-treasury-preview
python3 -m core.page --out _site
python3 -m pytest -q
node --test tests/js/*.test.js
```

The contributor's temporary GitHub Actions suite, likewise retained
only on the research branch, runs the offline tests, builds the
multilingual site with upstream's CJK fonts, and uploads the three
review-only SVGs and both historical-December and confirmed-annual
CSV audits. The [baseline full suite](https://github.com/glaucojrcarvalho/worldreports/actions/runs/40144541681)
passed **2,211 tests and 8 subtests**; newer source-annual
regressions are tested by the same focused commands above. This
PR does not change the site's nine published plates or its provenance
because no canonical fiscal plate is claimed.

## Publication gate / what is still missing

1. **Existing fiscal plate:** Upstream now publishes an IMF WEO
   general-government fiscal plate. This Treasury cash-budget series
   remains a separate national dataset, not a substitute for IMF general
   government or COFOG. A future cash-budget lens is an optional
   follow-up and must not occupy a canonical fiscal slot.
2. **December-to-annual explanation:** the exact official annual
   and December editions are now identified, and the later annual
   confirms NBU to one-decimal precision. A detailed administrative
   explanation of individual revised bookings is not proven and must
   not be invented. This is a documented publisher-edition seam, not a
   same-vintage cross-source blocker for a source-only PR.
3. **Final visual/editorial review:** confirm the generated Ukrainian,
   English and Portuguese charts and site/manifest statements against the
   exact branch tip, then attach the GitHub Actions gate result. Do not
   regenerate unrelated plates or modify the maintainer's repository.

The intended PR is a **focused Treasury fiscal source
enhancement**, not a replacement Ukraine atlas. No additional canonical
fiscal plate is claimed. Upstream's nine published chapters remain intact.
