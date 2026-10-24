#!/usr/bin/env python3
"""Stage Israel spending and living-standard series for review.

Usage: python3 -I countries/israel/fetch/fetch_spending_people.py

The script writes review sidecars only.  It never overwrites the curated
publication files.  Four independent sources are kept definition-safe:

* OECD National Accounts at a Glance, ``DF_NAAG_OTEF``: general-government
  expenditure by COFOG division, already expressed as a percentage of GDP.
* OECD National Accounts at a Glance, ``DF_NAAG_VI``: general-government
  gross fixed capital formation as a percentage of GDP.
* World Bank WDI ``NE.GDI.FTOT.ZS``: whole-economy GFCF as a percentage of
  GDP.  This is not government investment and is staged separately.
* OECD Income Distribution Database ``DF_IDD``: disposable-income Gini and
  relative poverty.  The 2011 and 2012 methodologies and the current/previous
  definitions remain separate columns; they are never spliced into a line.
* Israel National Insurance Institute (Bituach Leumi): effective-date history
  of the statutory adult monthly minimum wage.  Calendar-year averages are
  month-weighted and converted with the already curated annual-average ILS/USD
  series.  The incomplete 2026 annual average is deliberately omitted.

Outputs:
  data/spending/cofog_from_oecd.csv
  data/spending/public_investment_from_oecd.csv
  data/spending/whole_economy_investment_from_wb.csv
  data/social/income_distribution_from_oecd.csv
  data/social/minimum_wage_from_btl.csv
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
import urllib.request
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache" / "spending_people"

OECD_ACCEPT = "application/vnd.sdmx.data+csv;version=1.0.0"
OECD_BASE = "https://sdmx.oecd.org/public/rest/data/"
COFOG_URL = (
    OECD_BASE
    + "OECD.SDD.NAD,DSD_NAAG_VI@DF_NAAG_OTEF,/A.ISR.OTES13F"
      "...?startPeriod=2006&dimensionAtObservation=AllDimensions"
)
PUBLIC_INVESTMENT_URL = (
    OECD_BASE
    + "OECD.SDD.NAD,DSD_NAAG_VI@DF_NAAG_VI,/A.ISR.P51GS13"
      "...?startPeriod=2006&dimensionAtObservation=AllDimensions"
)
IDD_URL = (
    OECD_BASE
    + "OECD.WISE.INE,DSD_WISE_IDD@DF_IDD,/ISR.A."
      "INC_DISP_GINI+PR_INC_DISP......?startPeriod=2006"
      "&dimensionAtObservation=AllDimensions"
)
WB_URL = (
    "https://api.worldbank.org/v2/country/ISR/indicator/NE.GDI.FTOT.ZS"
    "?format=json&per_page=200&date=2006:2025"
)
BTL_URL = (
    "https://www.btl.gov.il/Mediniyut/GeneralData/Pages/"
    "%D7%A9%D7%9B%D7%A8%20%D7%9E%D7%99%D7%A0%D7%99%D7%9E%D7%95%D7%9D.aspx"
)
HEADERS = {"User-Agent": "worldreports.io data refresh"}

# The P51GS13 response is a fully specified National Accounts at a Glance
# slice, not merely any row carrying a familiar measure code.  Assert every
# fixed DSD dimension so a widened key, changed perimeter or changed accounting
# treatment cannot enter the cache unnoticed.
PUBLIC_INVESTMENT_DIMENSIONS = {
    "FREQ": "A",
    "REF_AREA": "ISR",
    "MEASURE": "P51GS13",
    "EXPENDITURE": "_T",
    "UNIT_MEASURE": "PT_B1GQ",
    "CHAPTER": "NAAG_VI",
    "ADJUSTMENT": "N",
    "COUNTERPART_AREA": "_Z",
    "SECTOR": "S13",
    "COUNTERPART_SECTOR": "_Z",
    "CONSOLIDATION": "N",
    "ACCOUNTING_ENTRY": "D",
    "TRANSACTION": "P51G",
    "INSTR_ASSET": "_Z",
    "MATURITY": "",
    "PRODUCT": "",
    "PENSION_FUNDTYPE": "",
    "CURRENCY_DENOM": "",
    "VALUATION": "",
    "PRICE_BASE": "V",
    "TRANSFORMATION": "N",
    "TABLE_IDENTIFIER": "",
    "REF_YEAR_PRICE": "",
    "BASE_PER": "",
    "CONF_STATUS": "F",
    "UNIT_MULT": "0",
    "CURRENCY": "_Z",
}


class FetchError(RuntimeError):
    pass


def _download(name: str, url: str, accept: str, validate) -> bytes:
    """Return a validated cached/downloaded payload; validate before cache."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / name
    if path.exists():
        raw = path.read_bytes()
        try:
            validate(raw)
            return raw
        except Exception as exc:  # noqa: BLE001
            print(f"stale cache {name} rejected: {exc}", file=sys.stderr)
            path.unlink()
    req = urllib.request.Request(url, headers={**HEADERS, "Accept": accept})
    with urllib.request.urlopen(req, timeout=120) as response:
        raw = response.read()
        content_type = response.headers.get_content_type()
    allowed = {
        "text/csv", "application/vnd.sdmx.data+csv", "application/json",
        "text/html", "application/xhtml+xml",
    }
    if content_type not in allowed:
        raise FetchError(f"{name}: unexpected content type {content_type}")
    validate(raw)
    path.write_bytes(raw)
    return raw


def _sdmx_rows(raw: bytes, required: set[str], minimum: int) -> list[dict[str, str]]:
    if raw.lstrip().startswith((b"<", b"{")):
        raise FetchError("OECD returned HTML/JSON instead of SDMX-CSV")
    try:
        rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    except UnicodeDecodeError as exc:
        raise FetchError("OECD response is not UTF-8 CSV") from exc
    fields = set(rows[0]) if rows else set()
    if len(rows) < minimum or not required <= fields:
        raise FetchError(
            f"OECD payload short or schema changed: {len(rows)} rows; "
            f"missing {sorted(required - fields)}"
        )
    return rows


def _write(path: Path, header: list[str], rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    path.write_text(buffer.getvalue(), encoding="utf-8")
    print(f"  {path.relative_to(ROOT)}: {len(rows)} rows")


def stage_cofog() -> None:
    required = {
        "REF_AREA", "FREQ", "MEASURE", "EXPENDITURE", "UNIT_MEASURE",
        "TIME_PERIOD", "OBS_VALUE", "SECTOR", "CONSOLIDATION", "TRANSACTION",
    }

    def validate(raw: bytes) -> None:
        rows = _sdmx_rows(raw, required, 200)
        if {r["REF_AREA"] for r in rows} != {"ISR"}:
            raise FetchError("COFOG country filter did not return Israel alone")

    raw = _download("oecd_cofog.csv", COFOG_URL, OECD_ACCEPT, validate)
    rows = _sdmx_rows(raw, required, 200)
    by_year: dict[int, dict[str, float]] = {}
    for row in rows:
        if not (
            row["REF_AREA"] == "ISR" and row["FREQ"] == "A"
            and row["MEASURE"] == "OTES13F"
            and row["UNIT_MEASURE"] == "PT_B1GQ"
            and row["SECTOR"] == "S13" and row["TRANSACTION"] == "OTE"
            and row["CONSOLIDATION"] == "P" and row["OBS_VALUE"]
        ):
            continue
        year = int(row["TIME_PERIOD"])
        code = row["EXPENDITURE"]
        if code in by_year.setdefault(year, {}):
            raise FetchError(f"duplicate COFOG observation {year} {code}")
        by_year[year][code] = float(row["OBS_VALUE"])

    divisions = [f"GF{i:02d}" for i in range(1, 11)]
    complete = sorted(y for y, v in by_year.items() if {"_T", *divisions} <= v.keys())
    if not complete or complete[0] != 2006 or complete[-1] < 2024:
        raise FetchError(f"unexpected COFOG coverage {complete[:1]}..{complete[-1:]}")
    out = []
    for year in complete:
        v = by_year[year]
        if abs(sum(v[c] for c in divisions) - v["_T"]) > 0.02:
            raise FetchError(f"{year}: COFOG divisions do not sum to total")
        out.append([
            year, v["_T"], v["GF10"], v["GF07"], v["GF09"], v["GF01"],
            v["GF04"], v["GF02"] + v["GF03"],
            v["GF05"] + v["GF06"] + v["GF08"],
        ])
    known = dict((r[0], r) for r in out)
    if abs(known[2020][1] - 45.6604361637678) > 0.001:
        raise FetchError(f"COFOG 2020 total changed: {known[2020][1]}")
    _write(
        DATA / "spending" / "cofog_from_oecd.csv",
        ["year", "total_pct_gdp", "social_protection_pct_gdp", "health_pct_gdp",
         "education_pct_gdp", "general_public_services_pct_gdp",
         "economic_affairs_pct_gdp", "defence_public_order_pct_gdp",
         "other_pct_gdp"],
        out,
    )


def stage_public_investment() -> None:
    required = set(PUBLIC_INVESTMENT_DIMENSIONS) | {
        "DATAFLOW", "TIME_PERIOD", "OBS_VALUE", "DECIMALS", "OBS_STATUS",
    }

    def validate(raw: bytes) -> None:
        rows = _sdmx_rows(raw, required, 15)
        if {row["REF_AREA"] for row in rows} != {"ISR"}:
            raise FetchError("public-investment response contains a non-Israel row")
        for row in rows:
            wrong = {
                key: (row[key], expected)
                for key, expected in PUBLIC_INVESTMENT_DIMENSIONS.items()
                if row[key] != expected
            }
            if wrong:
                raise FetchError(
                    "public-investment DSD dimensions changed for "
                    f"{row.get('TIME_PERIOD')}: {wrong}"
                )
            if row["OBS_STATUS"] != "A" or not row["OBS_VALUE"]:
                raise FetchError(
                    f"public-investment observation is missing/flagged: {row!r}"
                )

    raw = _download("oecd_public_investment.csv", PUBLIC_INVESTMENT_URL,
                    OECD_ACCEPT, validate)
    rows = _sdmx_rows(raw, required, 15)
    out = []
    for row in rows:
        if not (
            row["REF_AREA"] == "ISR" and row["FREQ"] == "A"
            and row["MEASURE"] == "P51GS13"
            and row["UNIT_MEASURE"] == "PT_B1GQ"
            and row["SECTOR"] == "S13" and row["TRANSACTION"] == "P51G"
            and row["OBS_VALUE"]
        ):
            continue
        out.append([int(row["TIME_PERIOD"]), float(row["OBS_VALUE"])])
    out.sort()
    if not out or out[0][0] != 2006 or out[-1][0] < 2024 or len({r[0] for r in out}) != len(out):
        raise FetchError(f"unexpected public-investment coverage/duplicates: {out[:1]}..{out[-1:]}")
    spot = dict(out)
    if abs(spot[2019] - 4.87010331401071) > 1e-6:
        raise FetchError(f"public investment 2019 changed: {spot[2019]}")
    _write(DATA / "spending" / "public_investment_from_oecd.csv",
           ["year", "gov_gfcf_pct_gdp"], out)


def stage_whole_economy_investment() -> None:
    def parse(raw: bytes) -> list[dict]:
        if raw.lstrip().startswith(b"<"):
            raise FetchError("World Bank returned HTML")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise FetchError("World Bank response is not JSON") from exc
        if not (isinstance(payload, list) and len(payload) == 2
                and isinstance(payload[0], dict) and isinstance(payload[1], list)):
            raise FetchError("World Bank payload shape changed")
        if payload[0].get("total", 0) < 15:
            raise FetchError("World Bank response unexpectedly short")
        for index, row in enumerate(payload[1]):
            if row.get("countryiso3code") != "ISR":
                raise FetchError(
                    f"World Bank row {index} is not Israel: "
                    f"{row.get('countryiso3code')!r}"
                )
            indicator = row.get("indicator")
            if not isinstance(indicator, dict) or indicator.get("id") != "NE.GDI.FTOT.ZS":
                raise FetchError(
                    f"World Bank row {index} has wrong indicator: {indicator!r}"
                )
        return payload[1]

    raw = _download("wb_gfcf.json", WB_URL, "application/json", parse)
    observations = parse(raw)
    out = sorted(
        [int(r["date"]), float(r["value"])]
        for r in observations
        if r.get("value") is not None
    )
    if not out or out[0][0] > 2006 or out[-1][0] < 2024:
        raise FetchError(f"unexpected WDI GFCF coverage: {out[:1]}..{out[-1:]}")
    spot = dict(out)
    if abs(spot[2019] - 23.1324217345266) > 1e-6:
        raise FetchError(f"WDI GFCF 2019 changed: {spot[2019]}")
    _write(DATA / "spending" / "whole_economy_investment_from_wb.csv",
           ["year", "gfcf_pct_gdp"], out)


def stage_income_distribution() -> None:
    required = {
        "REF_AREA", "FREQ", "MEASURE", "STATISTICAL_OPERATION",
        "UNIT_MEASURE", "AGE", "METHODOLOGY", "DEFINITION", "POVERTY_LINE",
        "TIME_PERIOD", "OBS_VALUE", "OBS_STATUS",
    }

    selected_coverage = {
        ("INC_DISP_GINI", "_T", "METH2011", "D_CUR", "_Z"):
            set(range(2008, 2012)),
        ("INC_DISP_GINI", "_T", "METH2012", "D_INC", "_Z"):
            set(range(2011, 2023)),
        ("INC_DISP_GINI", "_T", "METH2012", "D_CUR", "_Z"):
            {2023},
        ("PR_INC_DISP", "_T", "METH2011", "D_CUR", "PL_50"):
            set(range(2008, 2012)),
        ("PR_INC_DISP", "_T", "METH2012", "D_INC", "PL_50"):
            set(range(2011, 2023)),
        ("PR_INC_DISP", "_T", "METH2012", "D_CUR", "PL_50"):
            {2023},
        ("PR_INC_DISP", "Y_LT18", "METH2012", "D_INC", "PL_50"):
            set(range(2011, 2023)),
        ("PR_INC_DISP", "Y_LT18", "METH2012", "D_CUR", "PL_50"):
            {2023},
        ("PR_INC_DISP", "Y_GT65", "METH2012", "D_INC", "PL_50"):
            set(range(2011, 2023)),
        ("PR_INC_DISP", "Y_GT65", "METH2012", "D_CUR", "PL_50"):
            {2023},
    }

    def validate(raw: bytes) -> None:
        rows = _sdmx_rows(raw, required, 200)
        if {r["REF_AREA"] for r in rows} != {"ISR"} or {r["FREQ"] for r in rows} != {"A"}:
            raise FetchError("IDD key did not return annual Israel rows alone")
        observed: dict[tuple[str, str, str, str, str], set[int]] = {
            key: set() for key in selected_coverage
        }
        for row in rows:
            measure = row["MEASURE"]
            expected_unit = {
                "INC_DISP_GINI": "0_TO_1",
                "PR_INC_DISP": "PT_POP",
            }.get(measure)
            if expected_unit is None or row["UNIT_MEASURE"] != expected_unit:
                raise FetchError(
                    f"IDD measure/unit changed: {measure!r}/{row['UNIT_MEASURE']!r}"
                )
            if row["STATISTICAL_OPERATION"] != "_Z":
                raise FetchError(
                    "IDD returned a non-default statistical operation: "
                    f"{row['STATISTICAL_OPERATION']!r}"
                )
            key = (measure, row["AGE"], row["METHODOLOGY"],
                   row["DEFINITION"], row["POVERTY_LINE"])
            if key in observed and row["OBS_VALUE"]:
                if row["OBS_STATUS"] != "A":
                    raise FetchError(f"IDD selected observation is flagged: {row!r}")
                observed[key].add(int(row["TIME_PERIOD"]))
        wrong_coverage = {
            key: (sorted(observed[key]), sorted(expected))
            for key, expected in selected_coverage.items()
            if observed[key] != expected
        }
        if wrong_coverage:
            raise FetchError(
                "IDD selected methodology/definition coverage changed: "
                f"{wrong_coverage}"
            )

    raw = _download("oecd_idd.csv", IDD_URL, OECD_ACCEPT, validate)
    rows = _sdmx_rows(raw, required, 200)
    columns = {
        ("INC_DISP_GINI", "_T", "METH2011", "D_CUR", "_Z"):
            "gini_meth2011_current",
        ("INC_DISP_GINI", "_T", "METH2012", "D_INC", "_Z"):
            "gini_meth2012_previous",
        ("INC_DISP_GINI", "_T", "METH2012", "D_CUR", "_Z"):
            "gini_meth2012_current",
        ("PR_INC_DISP", "_T", "METH2011", "D_CUR", "PL_50"):
            "poverty50_pct_meth2011_current",
        ("PR_INC_DISP", "_T", "METH2012", "D_INC", "PL_50"):
            "poverty50_pct_meth2012_previous",
        ("PR_INC_DISP", "_T", "METH2012", "D_CUR", "PL_50"):
            "poverty50_pct_meth2012_current",
        ("PR_INC_DISP", "Y_LT18", "METH2012", "D_INC", "PL_50"):
            "child_poverty50_pct_meth2012_previous",
        ("PR_INC_DISP", "Y_LT18", "METH2012", "D_CUR", "PL_50"):
            "child_poverty50_pct_meth2012_current",
        ("PR_INC_DISP", "Y_GT65", "METH2012", "D_INC", "PL_50"):
            "old_age_poverty50_pct_meth2012_previous",
        ("PR_INC_DISP", "Y_GT65", "METH2012", "D_CUR", "PL_50"):
            "old_age_poverty50_pct_meth2012_current",
    }
    by_year: dict[int, dict[str, float]] = {}
    for row in rows:
        key = (row["MEASURE"], row["AGE"], row["METHODOLOGY"],
               row["DEFINITION"], row["POVERTY_LINE"])
        if key not in columns or not row["OBS_VALUE"]:
            continue
        year, col = int(row["TIME_PERIOD"]), columns[key]
        if col in by_year.setdefault(year, {}):
            raise FetchError(f"duplicate IDD observation {year} {col}")
        by_year[year][col] = float(row["OBS_VALUE"])
    names = list(columns.values())
    years = sorted(by_year)
    if not years or years[0] != 2008 or years[-1] < 2023:
        raise FetchError(f"unexpected IDD coverage {years[:1]}..{years[-1:]}")
    if abs(by_year[2023]["gini_meth2012_current"] - 0.34154999256134) > 1e-9:
        raise FetchError("IDD 2023 current-definition Gini changed")
    if abs(by_year[2023]["poverty50_pct_meth2012_current"] - 17.1729996800423) > 1e-8:
        raise FetchError("IDD 2023 current-definition poverty changed")
    out = [[year, *[by_year[year].get(name, "") for name in names]] for year in years]
    _write(DATA / "social" / "income_distribution_from_oecd.csv",
           ["year", *names], out)


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_cell = False
        self.cell: list[str] = []
        self.row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "tr":
            self.row = []
        elif tag in {"td", "th"}:
            self.in_cell = True
            self.cell = []

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"}:
            value = " ".join("".join(self.cell).replace("\u200b", "").split())
            if value:
                self.row.append(value)
            self.in_cell = False
        elif tag == "tr" and self.row:
            self.rows.append(self.row)


def _btl_levels(raw: bytes) -> list[tuple[date, float]]:
    try:
        html = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise FetchError("BTL page is not UTF-8 HTML") from exc
    if "<html" not in html.lower() or "שכר מינימום" not in html:
        raise FetchError("BTL response is not the Hebrew minimum-wage page")
    parser = _TableParser()
    parser.feed(html)
    date_re = re.compile(r"^(\d{1,2})[./](\d{1,2})[./](\d{4})$")
    number_re = re.compile(r"^\d[\d,]*\.\d+$")
    levels: dict[date, float] = {}
    for row in parser.rows:
        match = next((date_re.match(cell) for cell in row if date_re.match(cell)), None)
        if not match:
            continue
        candidates = [float(cell.replace(",", "")) for cell in row if number_re.match(cell)]
        if not candidates:
            continue
        effective = date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
        levels[effective] = max(candidates)  # monthly wage is the largest amount in the row
    out = sorted(levels.items())
    known = dict(out)
    for when, want in [(date(2006, 4, 1), 3456.58),
                       (date(2018, 4, 1), 5300.0),
                       (date(2025, 4, 1), 6247.67),
                       (date(2026, 4, 1), 6443.85)]:
        if abs(known.get(when, -1) - want) > 0.005:
            raise FetchError(f"BTL known value {when} changed/missing: {known.get(when)}")
    if len(out) < 20:
        raise FetchError(f"BTL history unexpectedly short: {len(out)} effective levels")
    return out


def stage_minimum_wage() -> None:
    raw = _download("btl_minimum_wage.html", BTL_URL, "text/html", _btl_levels)
    levels = _btl_levels(raw)
    fx_path = DATA / "markets" / "usdils.csv"
    with fx_path.open(encoding="utf-8") as handle:
        fx = {int(r["year"]): float(r["ils_per_usd"]) for r in csv.DictReader(handle)}
    out = []
    for year in range(2006, 2026):
        monthly = []
        changes = []
        for month in range(1, 13):
            when = date(year, month, 1)
            active = [(d, v) for d, v in levels if d <= when]
            if not active:
                raise FetchError(f"no BTL level active at {when}")
            monthly.append(active[-1][1])
        changes = [d.isoformat() for d, _ in levels if d.year == year]
        annual_ils = sum(monthly) / 12
        if year not in fx:
            raise FetchError(f"no curated annual-average ILS/USD rate for {year}")
        out.append([year, round(annual_ils, 4), fx[year], round(annual_ils / fx[year], 2),
                    ";".join(changes)])
    spot = dict((r[0], r) for r in out)
    if abs(spot[2017][1] - 5025.0) > 0.001:
        raise FetchError(f"2017 annual minimum should be ILS 5,025: {spot[2017][1]}")
    if abs(spot[2025][1] - 6155.7575) > 0.001:
        raise FetchError(f"2025 annual minimum changed: {spot[2025][1]}")
    _write(DATA / "social" / "minimum_wage_from_btl.csv",
           ["year", "monthly_ils_avg", "ils_per_usd_avg", "monthly_usd_avg",
            "effective_dates_in_year"], out)


def main() -> None:
    print("Staging Israel spending and people series (review sidecars only)")
    stage_cofog()
    stage_public_investment()
    stage_whole_economy_investment()
    stage_income_distribution()
    stage_minimum_wage()
    print("Done. Review sidecar diffs before deliberately promoting curated CSVs.")


if __name__ == "__main__":
    main()
