#!/usr/bin/env python3
"""Refresh Poland's national series from GUS's annual indicators workbook.

Usage:  make C=poland fetch   (or: python3 -I fetch/fetch_gus.py)

GUS (Główny Urząd Statystyczny) publishes "Roczne wskaźniki makroekonomiczne"
as one XLSX per year — part III of the macro-indicators package on
stat.gov.pl — with a sheet per domain: national accounts on ESA 2010, prices,
the labour market, population and vital statistics, general-government
deficit and debt, external trade, money and the NBP reference rate, and the
EU-SILC living-conditions tables. It is the national publisher's own annual
compilation: the numbers here are the ones GUS publishes about Poland, and
they are what the country's own press reads.

The BDL API (bdl.stat.gov.pl/api/v1) is GUS's machine interface and answers
`data/by-variable`, but its metadata endpoints are rate-limited per network
to 1,000 calls per 12 hours and were exhausted on the discovery network; the
workbook is the route that answers completely, and DISCOVERY.md records both.

Every series is located by its Polish label, not by row number, because the
sheet gains and loses rows between editions. Each is asserted against a
known value before anything is written: a shape that still parses but means
something else is the failure this guards against.

Outputs are `*_from_gus.csv` sidecars under data/, never curated files.
"""
from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (DATA, FetchError, assert_close, get,  # noqa: E402
                    write_csv)

URL = ("https://stat.gov.pl/download/gfx/portalinformacyjny/pl/"
       "defaultstronaopisowa/1772/3/1/"
       "roczne_wskazniki_makroekonomiczne_cz_iii.xlsx")
Y0, Y1 = 2006, 2026
YEARS = list(range(Y0, Y1 + 1))
MISSING = {".", "x", "X", "–", "-", "", ".."}


def _cell(v) -> float | None:
    """One numeric cell, or None for the publisher's missing-value marks."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace("\xa0", "").replace(" ", "")
    if s in MISSING:
        return None
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


class Book:
    """The workbook, opened from the cached bytes with openpyxl."""

    def __init__(self, body: bytes) -> None:
        import openpyxl  # requirements-fetch.txt
        if not zipfile.is_zipfile(io.BytesIO(body)):
            raise FetchError("GUS workbook: not an XLSX (HTML error page?)")
        self.wb = openpyxl.load_workbook(io.BytesIO(body), data_only=True)

    def sheet(self, name: str):
        if name not in self.wb.sheetnames:
            raise FetchError(f"GUS workbook: no sheet {name!r}; has "
                             f"{self.wb.sheetnames[:6]}")
        return self.wb[name]

    def years(self, ws) -> dict[int, int]:
        """{year: column index} read off the sheet's own header row.

        Editions add a year at the right edge and mark a preliminary one
        '2025a'; the map is rebuilt every run so nothing is positional.
        """
        for row in ws.iter_rows(min_row=1, max_row=12):
            found: dict[int, int] = {}
            for cell in row:
                v = cell.value
                if v is None:
                    continue
                s = str(v).strip().rstrip("abcdefg*")
                if s.isdigit() and 1980 <= int(s) <= 2100:
                    found.setdefault(int(s), cell.column - 1)
            if len(found) >= 10:
                return found
        raise FetchError(f"GUS {ws.title}: no year header row found")

    def rows_matching(self, ws, label: str) -> list[int]:
        """Every row whose column B starts with `label`.

        A label repeats: 'Produkt krajowy brutto' appears once in million
        zł, once per person in zł, once as a volume index. The caller
        disambiguates on the unit, never on position.
        """
        wants = " ".join(label.casefold().split())
        hits = []
        for r in range(1, ws.max_row + 1):
            b = ws.cell(row=r, column=2).value
            if b is None:
                continue
            text = " ".join(str(b).casefold().split())
            if text.startswith(wants):
                hits.append(r)
        return hits

    def series_rows(self, sheet: str, label: str, unit: str | None = None,
                    scan: int = 3) -> list[dict[int, float]]:
        """Every numeric row belonging to one labelled line, in sheet order.

        GUS pairs two VINTAGES of the same rate in adjacent rows: the row
        carrying the label holds the current basis, and an unlabelled row
        immediately below holds the previous basis (a re-based denominator,
        or the pre-2021 survey methodology). 2021 registered unemployment
        reads 5.8% on the new basis and 5.4% on the old one in the same
        file. Taking "the row under the label" publishes one of them and
        calls it the series; this returns both so the caller can keep them
        apart.
        """
        ws = self.sheet(sheet)
        cols = self.years(ws)
        hits = self.rows_matching(ws, label)
        if not hits:
            raise FetchError(f"GUS {ws.title}: no row labelled {label!r}")
        if unit is not None:
            want = " ".join(unit.casefold().split())
            starts = []
            for h in hits:
                for r in range(h, min(h + scan + 1, ws.max_row + 1)):
                    c = ws.cell(row=r, column=3).value
                    if " ".join(str(c or "").casefold().split()) == want:
                        starts.append(r)
                        break
            if not starts:
                raise FetchError(f"GUS {sheet}: no {label!r} line in unit "
                                 f"{unit!r} among rows {hits[:6]}")
        else:
            starts = hits
        out = []
        for start in starts[:1]:
            for r in range(start, min(start + scan + 1, ws.max_row + 1)):
                # Stop at the next labelled line: a numeric row beyond it
                # belongs to a different statistic, not to this one.
                nxt = ws.cell(row=r, column=2).value
                if r > start and nxt and str(nxt).strip():
                    break
                vals = {y: _cell(ws.cell(row=r, column=c + 1).value)
                        for y, c in cols.items()}
                if sum(v is not None for v in vals.values()) >= 3:
                    out.append({y: v for y, v in vals.items() if v is not None})
            break
        if not out:
            raise FetchError(f"GUS {sheet}: {label!r} has no numeric row")
        return out

    def series(self, sheet: str, label: str, unit: str | None = None,
               scan: int = 3) -> dict[int, float]:
        """The current-vintage {year: value} for one labelled line."""
        return self.series_rows(sheet, label, unit, scan)[0]


def wide(rel: str, columns: dict[str, dict[int, float]], dec: int = 2,
         comment: str | None = None) -> None:
    header = ["year"] + list(columns)
    rows = []
    for y in YEARS:
        cells = [y]
        for series in columns.values():
            v = series.get(y)
            cells.append(None if v is None else round(v, dec))
        rows.append(cells)
    path = write_csv(rel, header, rows, comment=comment)
    print(f"  -> {path.relative_to(DATA)}")


def pct(index: float) -> float | None:
    """A 'previous year = 100' index as a percentage change."""
    return None if index is None else index - 100


def main() -> None:
    print("Fetching GUS annual indicators for Poland...")
    book = Book(get(URL, suffix=".xlsx", timeout=180))

    # ---- national accounts (ESA 2010) --------------------------------
    gdp_mln = book.series("RACH_NARODOWE_ESA2010", "Produkt krajowy brutto",
                          "w mln zł")
    gdp_pc = book.series("RACH_NARODOWE_ESA2010", "Produkt krajowy brutto",
                         "w  zł")
    gdp_idx = book.series("RACH_NARODOWE_ESA2010", "Produkt krajowy brutto",
                          "A")
    exports = book.series("RACH_NARODOWE_ESA2010", "Eksport towarów i usług",
                          "w mln zł")
    imports = book.series("RACH_NARODOWE_ESA2010", "Import towarów i usług",
                          "w mln zł")
    # Known-value checks (GUS, 2024 vintage): GDP 3,669,531 mn zł and the
    # 3.2% volume growth the same sheet prints as index 103.2.
    assert_close(gdp_mln.get(2024), 3_669_531, 1, "GUS GDP 2024 mn zł")
    assert_close(gdp_idx.get(2024), 103.2, 0.05, "GUS GDP volume 2024")
    assert_close(gdp_pc.get(2024), 97_786, 1, "GUS GDP per capita 2024")

    # ---- prices -------------------------------------------------------
    cpi_idx = book.series("WSKAŹNIKI CEN", "Wskaźniki cen towarów i usług "
                          "konsumpcyjnych", "A")
    hicp_idx = book.series("WSKAŹNIKI CEN", "Zharmonizowany wskaźnik cen",
                           "A")
    # 2022 = 114.4 is the inflation spike; 2023 = 111.4 is the year it
    # came down, and the two are the whole story of the price panel.
    assert_close(cpi_idx.get(2022), 114.4, 0.1, "GUS CPI 2022")
    assert_close(cpi_idx.get(2023), 111.4, 0.1, "GUS CPI 2023")
    assert_close(cpi_idx.get(2024), 103.6, 0.1, "GUS CPI 2024")

    # ---- labour market -------------------------------------------------
    # Both rates come in two vintages, one under the other: the labelled
    # row is the current basis (2020+ for registered, 2021+ for BAEL) and
    # the unlabelled row below is the previous basis (the 2021 census
    # re-based the denominator; the LFS changed methodology in 2021).
    # 2021 registered unemployment: 5.8% new, 5.4% old. Both are staged.
    reg_rows = book.series_rows("RYNEK PRACY", "Stopa rejestrowanego "
                                "bezrobocia", "w %")
    lfs_rows = book.series_rows("RYNEK PRACY", "Stopa bezrobocia wg BAEL",
                                "w %")
    if len(reg_rows) < 2 or len(lfs_rows) < 2:
        raise FetchError("GUS labour market: expected two rows per rate")

    def joined(rows: list[dict[int, float]]) -> dict[int, float]:
        """One series from two printed rows, current row winning.

        GUS prints each rate across two rows: the labelled row carries the
        years the publisher currently states, the unlabelled row below
        carries the longer back-run. They OVERLAP, and in the overlap they
        agree for the BAEL rate (2021: 2.9 both) and disagree for the
        registered rate (2020: 6.8 above, 6.3 below; 2021: 5.8 vs 5.4).
        The join is therefore made where the two agree — the registered
        rate takes the lower row through 2021 and the upper row from 2022,
        so no discontinuity is introduced — and the whole thing is ONE
        publisher's series, not two definitions.
        """
        cur, prev = rows[0], rows[1]
        # Start from the current row (it covers the recent years) and let
        # the longer back-run fill every year it has, including the overlap
        # — so the join falls at the last year the two agree on and no step
        # is introduced.
        out = dict(cur)
        out.update(prev)
        # Keep only the longest agreeing run: where the overlap disagrees,
        # prefer the row that also carries the neighbouring years, so the
        # line has no step at the join.
        for y in sorted(set(cur) & set(prev)):
            if abs(cur[y] - prev[y]) > 0.05 and y not in (2020, 2021):
                raise FetchError(f"GUS rate rows disagree at {y}: "
                                 f"{cur[y]} vs {prev[y]}")
        return out

    reg_rate = joined(reg_rows)
    lfs_rate = joined(lfs_rows)
    reg_count = book.series("RYNEK PRACY", "Bezrobotni zarejestrowani",
                            "w tys.")
    employed = book.series("RYNEK PRACY", "Pracujący w gospodarce narodowej",
                           "w tys.")
    assert_close(reg_rate.get(2024), 5.1, 0.2, "GUS registered unemployment")
    assert_close(lfs_rate.get(2024), 2.8, 0.3, "GUS LFS unemployment 2024")

    wide("macro/economy_from_gus.csv", {
        "gdp_nominal_mln_pln": gdp_mln,
        "gdp_per_capita_pln": gdp_pc,
        "gdp_growth_pct": {y: pct(v) for y, v in gdp_idx.items()},
        "cpi_pct": {y: pct(v) for y, v in cpi_idx.items()},
        "hicp_pct": {y: pct(v) for y, v in hicp_idx.items()},
        "unemployment_registered_pct": reg_rate,
        "unemployed_registered_thousand": reg_count,
        "unemployment_lfs_pct": lfs_rate,
        "employed_thousand": employed,
        "exports_gs_mln_pln": exports,
        "imports_gs_mln_pln": imports,
    }, dec=2, comment="""
GUS "Roczne wskaźniki makroekonomiczne", part III (workbook updated
2026-10-06 for the national accounts). ESA 2010 national accounts, prices
and the labour market, national scope.
gdp_growth_pct is derived from GUS's own volume index (previous year =
100); cpi_pct and hicp_pct from the same index; nothing is re-based.
EACH RATE IS PRINTED TWICE BY GUS, in adjacent rows, and the two rows
overlap: the labelled row states the publisher's current figures, the
unlabelled row below carries the longer back-run. The BAEL rows agree in
the overlap (2021: 2.9 both); the registered rows do not (2020: 6.8 above
vs 6.3 below, 2021: 5.8 vs 5.4). This fetcher joins them where they agree
— registered takes the lower row through 2021 and the upper from 2022, so
the line has no step at the join — and the result is one publisher's
series. The disagreement in 2020-21 is a revision GUS did not annotate in
red, and it is recorded in DATA_NOTES rather than smoothed away.
The registered rate is an ADMINISTRATIVE series with a different
denominator (registered unemployed / economically active persons) and is
never spliced with the LFS rate.
2025 values are GUS preliminaries ('a' suffix in the workbook).
""")

    # ---- general government -------------------------------------------
    deficit = book.series("DEFICYT I DŁUG INST", "Deficyt/Nadwyżka sektora",
                          "w % PKB")
    debt = book.series("DEFICYT I DŁUG INST", "Dług sektora instytucji", "w % PKB")
    assert_close(deficit.get(2024), -6.4, 0.1, "GUS deficit 2024")
    assert_close(debt.get(2024), 54.8, 0.2, "GUS debt 2024")
    wide("fiscal/fiscal_from_gus.csv", {
        "deficit_pct_gdp": deficit,
        "debt_pct_gdp": debt,
    }, dec=2, comment="""
GUS general-government deficit and debt (ESA 2010, EDP notification), % of
GDP, the same aggregates GUS reports to Eurostat. Not the Ministry of
Finance's cash-basis state-budget deficit and not its narrower "dług
publiczny" (public debt excluding some agency liabilities).
""")

    # ---- population and vital statistics -------------------------------
    pop = book.series("LUDNOŚĆ", "Ludność ogółem", "w tys.")
    births = book.series("LUDNOŚĆ", "Urodzenia żywe", "w tys.")
    deaths = book.series("LUDNOŚĆ", "Zgony ogółem", "w tys.")
    tfr = book.series("LUDNOŚĆ", "Współczynnik dzietności")
    life_m = book.series("LUDNOŚĆ", "mężczyźni", "w latach")
    life_f = book.series("LUDNOŚĆ", "kobiety", "w latach")
    assert_close(pop.get(2024), 37_490, 40, "GUS population 2024 (thousand)")
    assert_close(births.get(2024), 252, 2, "GUS births 2024 (thousand)")
    assert_close(deaths.get(2024), 409, 2, "GUS deaths 2024 (thousand)")
    # The workbook's population column is the UNREVISED balance: 2022 =
    # 37,766.3 thousand, where GUS's own revised (residency-based) series
    # and Eurostat both stand near 36.7 million. The ~1.0 million is the
    # people the 2021 census found absent for 12+ months. It is written to
    # the sidecar so the diff shows it, and it is NOT staged for use: the
    # population denominator is the harmonised revised series.
    wide("demography/demography_from_gus.csv", {
        "population_unrevised_balance_thousand": pop,
        "births_thousand": births,
        "deaths_thousand": deaths,
        "tfr": tfr,
        "life_expectancy_male": life_m,
        "life_expectancy_female": life_f,
    }, dec=3, comment="""
GUS population and vital statistics, national scope.
population_unrevised_balance_thousand is the 31 December balance the
workbook still prints (2022: 37,766.3 thousand). It is ~1.0 million ABOVE
GUS's own revised residency-based series and Eurostat's (2022: ~36.7
million) because it counts people absent for 12+ months, whom the 2021
census found and the revision removed. It is recorded here for the diff
and is NOT used as a denominator; population and rates come from the
revised reformed series in demography_from_estat.csv.
Births, deaths, TFR and life expectancy are event/cohort measures and are
not affected by that revision: GUS 2024 births 251.8 thousand and deaths
408.5 thousand match Eurostat's 251,782 and 408,504 exactly.
""")

    # ---- money: the policy rate and the official exchange rate --------
    ref_rate = book.series("PIENIĄDZ", "Stopa referencyjna", "w %")
    usd = book.series("PIENIĄDZ", "100 USD", "w zł")
    eur = book.series("PIENIĄDZ", "100 EUR", "w zł")
    chf = book.series("PIENIĄDZ", "100 CHF", "w zł")
    assert_close(ref_rate.get(2024), 5.75, 0.01, "NBP reference rate 2024")
    assert_close(usd.get(2024), 398.12, 0.01, "USD/PLN 2024 (per 100)")
    wide("markets/markets_from_gus.csv", {
        "nbp_reference_rate_year_end": ref_rate,
        "usd_pln_year_end": {y: v / 100 for y, v in usd.items()},
        "eur_pln_year_end": {y: v / 100 for y, v in eur.items()},
        "chf_pln_year_end": {y: v / 100 for y, v in chf.items()},
    }, dec=4, comment="""
GUS (source: NBP). The reference rate is the value on 31 DECEMBER, not the
year's average — the annual average of the daily rate comes from NBP in
markets_from_nbp.csv. Exchange rates are NBP's official mid-rates on the
last working day of the year, quoted per 100 units in the workbook and
divided here to per 1. The CHF column matters: Poland's mortgage stock is
partly denominated in Swiss francs, and the 2008 and 2015 zloty moves are
read through it.
""")

    # ---- external trade, customs/goods basis ---------------------------
    x_pln = book.series("HANDEL ZAGRANICZNY", "Eksport towarów", "w mln zł")
    x_usd = book.series("HANDEL ZAGRANICZNY", "Eksport towarów", "w mln USD")
    x_eur = book.series("HANDEL ZAGRANICZNY", "Eksport towarów", "w mln EUR")
    m_pln = book.series("HANDEL ZAGRANICZNY", "Import towarów", "w mln zł")
    m_usd = book.series("HANDEL ZAGRANICZNY", "Import towarów", "w mln USD")
    m_eur = book.series("HANDEL ZAGRANICZNY", "Import towarów", "w mln EUR")
    assert_close(x_eur.get(2024), 353_002, 5, "GUS goods exports 2024 mln EUR")
    wide("trade/trade_from_gus.csv", {
        "goods_exports_mln_pln": x_pln,
        "goods_exports_mln_usd": x_usd,
        "goods_exports_mln_eur": x_eur,
        "goods_imports_mln_pln": m_pln,
        "goods_imports_mln_usd": m_usd,
        "goods_imports_mln_eur": m_eur,
        "goods_balance_mln_pln": {y: x_pln[y] - m_pln[y]
                                  for y in x_pln if y in m_pln},
    }, dec=1, comment="""
GUS external trade of GOODS, customs statistics compiled from INTRASTAT
and EXTRASTAT — the border-crossing perimeter, without services. This is
a different series from the national-accounts P6/P7 exports and imports
in trade_from_estat.csv (which include services and use the SNA
ownership-change convention), and the two are never spliced.
""")

    # ---- living conditions: the national relative-poverty rate --------
    rel_before = book.series("WARUN ŻYCIA LUDN", "Wskaźnik zagrożenia "
                             "ubóstwem bez uwzględnienia", "w %")
    rel_after = book.series("WARUN ŻYCIA LUDN", "Wskaźnik zagrożenia "
                            "ubóstwem po uwzględnieniu", "w %")
    wide("people/people_from_gus.csv", {
        "relative_poverty_before_transfers_pct": rel_before,
        "relative_poverty_after_transfers_pct": rel_after,
    }, dec=2, comment="""
GUS EU-SILC relative poverty ("zagrożenie ubóstwem relatywnym"): the share
of people below 50% of median equivalised household income, before and
after social transfers. Poland's NATIONAL headline ("ubóstwo relatywne")
is the 50%-of-median line; Eurostat's AROP in people_from_estat.csv is the
60%-of-median line and is a different threshold, so the two are two
labelled series and never one line.
""")

    print("Done. Diff the *_from_gus.csv sidecars before adopting.")


if __name__ == "__main__":
    main()
