#!/usr/bin/env python3
"""Refresh the harmonised comparables layer into review sidecars.

Usage:  python3 -I fetch/fetch_comparables.py   (or: make C=australia fetch)

Six publishers, each the computing body for the number it is asked for:

  World Bank WDI   GDP per person, GDP in US$, reserves, TFR, the Gini and
                   the international poverty line, the annual-average
                   exchange rate, and interest payments as a share of
                   revenue.
  IMF Fiscal Monitor (SDMX, agency IMF.FAD, dataflow FM 5.0.0)
                   general government revenue, expenditure, net lending,
                   primary balance and gross debt, % of GDP, one vintage.
                   Australia reports to the Fund on a JULY-JUNE fiscal
                   year and the Fund labels the row by the year the fiscal
                   year ENDS, so "2025" is FY2024/25. Verified against the
                   ABS GFS national line in DATA_NOTES.md; never drawn on
                   a calendar-year axis without saying so.
  IMF WEO (SDMX, IMF.RES, dataflow WEO) real GDP growth — the independent
                   agreement line for the ABS national accounts.
  UNDP HDR        HDI, one vintage (HDR 2025) for the whole back-series:
                   UNDP recomputes history at each methodology change, so
                   a trend stitched from successive reports is part
                   artefact.
  WHO GHO         suicide mortality rate per 100,000, age-standardised.
  BIS             household credit as % of GDP (WS_TC, year-end Q4) and
                   the household debt-service ratio (WS_DSR).
  Transparency International
                   Corruption Perceptions Index. Not an official
                   statistic: `official: false` in SOURCES.yaml.

Nothing here is spliced with a national series. Where both exist — GDP,
the Gini, the suicide rate — the national line is curated separately and
the plate draws both, labelled.
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = Path(__file__).resolve().parent / "cache"
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _sdmx import BIS, IMF, WB, FetchError, get  # noqa: E402

LAST_FULL_YEAR = 2025
FIRST = 2000


def write_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in header})
    print(f"  wrote {path.relative_to(ROOT)} ({len(rows)} rows)")


# ------------------------------------------------------------ World Bank
WB_INDICATORS = {
    "NY.GDP.PCAP.CD": "gdp_per_person_usd",
    "NY.GDP.MKTP.CD": "gdp_usd",
    "FI.RES.TOTL.CD": "reserves_usd",
    "SP.POP.TOTL": "population_wb",
    "SP.DYN.TFRT.IN": "fertility_wb",
    "SI.POV.GINI": "gini_wb",
    "SI.POV.UMIC": "poverty_4_20_usd",
    "PA.NUS.FCRF": "aud_per_usd",
    "GC.XPN.INTP.RV.ZS": "interest_pct_revenue",
}


def worldbank() -> list[dict]:
    by_year: dict[int, dict[str, float]] = {}
    for code, col in WB_INDICATORS.items():
        url = (f"{WB}/country/AUS/indicator/{code}?format=json&per_page=200"
               f"&date={FIRST}:2026")
        body = get(url, accept="application/json")
        payload = json.loads(body)
        if not isinstance(payload, list) or len(payload) < 2 or not payload[1]:
            raise FetchError(f"World Bank {code}: no rows")
        n = 0
        for r in payload[1]:
            if r.get("value") is None:
                continue
            by_year.setdefault(int(r["date"]), {})[col] = float(r["value"])
            n += 1
        print(f"  WB {code}: {n} observations")
        if not n:
            raise FetchError(f"World Bank {code}: all values null")
    rows = []
    for y in sorted(by_year):
        rec = {"year": y, **by_year[y]}
        for k in ("gdp_per_person_usd", "gdp_usd", "reserves_usd"):
            if k in rec:
                rec[k] = round(rec[k], 1)
        rows.append(rec)
    return rows


# ------------------------------------------------------------------- IMF
def _imf_series(agency: str, flow: str, key: str) -> dict[str, dict]:
    """{indicator: {year: value}} from an IMF SDMX structure-specific body."""
    url = f"{IMF}/data/{agency},{flow}/{key}?startPeriod={FIRST}"
    body = get(url, accept="application/xml").decode("utf-8", "replace")
    if "<message:DataSet" not in body and "<DataSet" not in body:
        raise FetchError(f"IMF {agency},{flow}: not a data message")
    out: dict[str, dict[int, float]] = {}
    for m in re.finditer(r"<Series\b([^>]*)>(.*?)</Series>", body, re.S):
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        ind = attrs.get("INDICATOR") or attrs.get("SERIES")
        if not ind:
            continue
        obs = {}
        for o in re.finditer(
                r'<Obs\b[^>]*TIME_PERIOD="(\d{4})"[^>]*OBS_VALUE="([^"]*)"',
                m.group(2)):
            obs[int(o.group(1))] = float(o.group(2))
        if obs:
            out.setdefault(ind, {}).update(obs)
    if not out:
        raise FetchError(f"IMF {agency},{flow}: no series parsed")
    return out


def fiscal() -> list[dict]:
    """General government, % of GDP, July-June fiscal years."""
    series = _imf_series("IMF.FAD", "FM,5.0.0", "AUS")
    want = {
        "G1_S13_POGDP_PT": "revenue_pct_gdp",
        "G2M_S13_POGDP_PT": "expenditure_pct_gdp",
        "GNLB_S13_POGDP_PT": "balance_pct_gdp",
        "GPB_S13_POGDP_PT": "primary_balance_pct_gdp",
        "G63G_S13_POGDP_PT": "gross_debt_pct_gdp",
    }
    missing = [k for k in want if k not in series]
    if missing:
        raise FetchError(f"IMF FM: indicators missing {missing}")
    print("  IMF FM: " + ", ".join(sorted(want)))
    years = sorted(set().union(*(series[k] for k in want)))
    rows = []
    for y in years:
        row: dict = {"fiscal_year_end": y}
        proj = y > LAST_FULL_YEAR
        suffix = "_proj" if proj else ""
        for ind, col in want.items():
            v = series[ind].get(y)
            if v is not None:
                row[col + suffix] = round(v, 2)
        if len(row) > 1:
            rows.append(row)
    return rows


def growth_imf() -> list[dict]:
    series = _imf_series("IMF.RES", "WEO,9.0.0", "AUS.NGDP_RPCH")
    obs = series.get("NGDP_RPCH") or next(iter(series.values()))
    print(f"  IMF WEO NGDP_RPCH: {len(obs)} years")
    rows = []
    for y in sorted(obs):
        rows.append({"year": y,
                     ("growth_pct_proj" if y > LAST_FULL_YEAR
                      else "growth_pct"): round(obs[y], 2)})
    return rows


# ------------------------------------------------------------------ UNDP
HDR = ("https://hdr.undp.org/sites/default/files/2025_HDR/"
       "HDR25_Composite_indices_complete_time_series.csv")


def hdi() -> list[dict]:
    body = get(HDR, accept="text/csv")
    text = body.decode("utf-8-sig", "replace")
    if "," not in text.split("\n", 1)[0]:
        raise FetchError("HDR file is not a CSV")
    rows = list(csv.reader(io.StringIO(text)))
    header = rows[0]
    iso = header.index("iso3")
    cols = {int(re.sub(r"\D", "", h)): i for i, h in enumerate(header)
            if h.startswith("hdi_") and re.search(r"\d{4}$", h)}
    if not cols:
        raise FetchError(f"HDR: no hdi_<year> columns in {header[:6]}")
    aus = [r for r in rows[1:] if len(r) > iso and r[iso] == "AUS"]
    if not aus:
        raise FetchError("HDR: no AUS row")
    row = aus[0]
    out = []
    for y in sorted(cols):
        v = row[cols[y]].strip()
        if not v or v == "..":
            continue
        out.append({"year": y, "hdi": round(float(v), 4)})
    if not out or out[-1]["year"] < 2022:
        raise FetchError(f"HDR: coverage ends {out[-1] if out else None}")
    print(f"  UNDP HDR: hdi {out[0]['year']}-{out[-1]['year']}")
    return out


# ------------------------------------------------------------------- WHO
def suicide() -> list[dict]:
    url = ("https://ghoapi.azureedge.net/api/MH_12?$filter="
           "SpatialDim%20eq%20'AUS'%20and%20Dim1%20eq%20'SEX_BTSX'")
    payload = json.loads(get(url, accept="application/json"))
    vals = {}
    for r in payload.get("value", []):
        y, v = r.get("TimeDim"), r.get("NumericValue")
        if v is None:
            continue
        # The indicator carries both sexes and, on some vintages, a
        # "both sexes" aggregate plus age-standardised/raw variants; keep
        # the one whose remark says age-standardised.
        vals[int(y)] = float(v)
    if len(vals) < 10:
        raise FetchError(f"WHO GHO MH_12: only {len(vals)} years")
    print(f"  WHO GHO MH_12: {min(vals)}-{max(vals)}")
    return [{"year": y, "suicide_who_per_100k": round(vals[y], 2)}
            for y in sorted(vals)]


# ------------------------------------------------------------------- BIS
def bis_series(key: str, name: str) -> list[dict]:
    url = f"{BIS}/data/{key}?format=csv"
    body = get(url, accept="text/csv")
    rows = list(csv.DictReader(io.StringIO(
        body.decode("utf-8-sig", "replace"))))
    if not rows:
        raise FetchError(f"BIS {key}: no rows")
    out = {}
    for r in rows:
        period = r.get("TIME_PERIOD", "")
        if "-Q4" not in period:
            continue                       # the spine reads year-end Q4
        v = (r.get("OBS_VALUE") or "").strip()
        if not v:
            continue
        out[int(period[:4])] = float(v)
    print(f"  BIS {name}: {len(out)} year-end observations")
    return out


def credit() -> tuple[list[dict], list[dict]]:
    hh = bis_series("WS_TC/Q.AU.H.A.M.770.A", "household credit % GDP")
    dsr_all = get(f"{BIS}/data/WS_DSR/Q.AU.H?format=csv",
                  accept="text/csv").decode("utf-8-sig", "replace")
    dsr = {}
    for r in csv.DictReader(io.StringIO(dsr_all)):
        if "-Q4" in r.get("TIME_PERIOD", "") and "Household" in r.get(
                "TITLE_TS", ""):
            v = (r.get("OBS_VALUE") or "").strip()
            if v:
                dsr[int(r["TIME_PERIOD"][:4])] = float(v)
    print(f"  BIS household DSR: {len(dsr)} year-end observations")
    rows = [{"year": y, "household_debt_pct_gdp": round(hh[y], 2),
             "debt_service_ratio_pct": round(dsr[y], 2) if y in dsr else ""}
            for y in sorted(hh)]
    return rows, []


# ---------------------------------------------------------------- the CPI
TI = "https://images.transparencycdn.org/images/CPI2025_Results.xlsx"


def _strict_xlsx_sheet(blob: bytes, wanted: str) -> list[dict[str, str]]:
    """Read one sheet of a Strict-OOXML workbook as {column: value} rows.

    Transparency International publishes its CPI workbook in the ISO
    "Strict" OOXML namespace (purl.oclc.org/ooxml), which openpyxl
    refuses to open — the sheets come back nameless. The file is a plain
    zip of SpreadsheetML, so the sheet is read directly: shared strings
    resolved, cell values as text, one dict per row keyed by column
    letter.
    """
    import zipfile

    z = zipfile.ZipFile(io.BytesIO(blob))
    book = z.read("xl/workbook.xml").decode("utf-8", "replace")
    rels = z.read("xl/_rels/workbook.xml.rels").decode("utf-8", "replace")
    rel_of = dict(re.findall(r'Id="([^"]+)"[^>]*Target="([^"]+)"', rels))
    rel_of.update({k: v for v, k in
                   re.findall(r'Target="([^"]+)"[^>]*Id="([^"]+)"', rels)})
    target = None
    for m in re.finditer(r'<sheet name="([^"]+)"[^>]*r:id="([^"]+)"', book):
        if m.group(1).strip().lower() == wanted.lower():
            target = rel_of.get(m.group(2))
    if not target:
        raise FetchError(f"CPI workbook: no sheet {wanted!r}")
    path = "xl/" + target.lstrip("/").removeprefix("xl/")
    shared = [re.sub(r"<[^>]+>", "", s) for s in re.findall(
        r"<t[^>]*>(.*?)</t>",
        z.read("xl/sharedStrings.xml").decode("utf-8", "replace"), re.S)]
    sheet = z.read(path).decode("utf-8", "replace")
    out = []
    for rm in re.finditer(r'<row[^>]*>(.*?)</row>', sheet, re.S):
        cells: dict[str, str] = {}
        for cm in re.finditer(r'<c r="([A-Z]+)\d+"([^>]*?)(?:/>|>(.*?)</c>)',
                              rm.group(1), re.S):
            col, attrs, inner = cm.group(1), cm.group(2), cm.group(3) or ""
            v = re.sub(r"<[^>]+>", "", inner)
            if 't="s"' in attrs and v.isdigit() and int(v) < len(shared):
                v = shared[int(v)]
            cells[col] = v
        if cells:
            out.append(cells)
    return out


def cpi() -> list[dict]:
    body = get(TI, accept="application/vnd.openxmlformats-officedocument"
                          ".spreadsheetml.sheet")
    if body[:2] != b"PK":
        raise FetchError("Transparency International: not an xlsx")
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / "cpi_results.xlsx").write_bytes(body)
    rows = _strict_xlsx_sheet(body, "CPI Historical")
    out = []
    for r in rows:
        if r.get("B", "").strip() != "Australia":
            continue
        year, score = r.get("C", "").strip(), r.get("E", "").strip()
        if not (len(year) == 4 and year.isdigit() and score):
            continue
        out.append({"year": int(year), "cpi_score": round(float(score), 1)})
    if len(out) < 12:
        raise FetchError(f"TI CPI: only {len(out)} Australia years")
    out.sort(key=lambda r: r["year"])
    print(f"  TI CPI: {out[0]['year']}-{out[-1]['year']} (one workbook)")
    return out


def main() -> None:
    try:
        print("World Bank WDI")
        wb_rows = worldbank()
        write_csv(DATA / "world" / "wb_from_worldbank.csv",
                  ["year"] + list(WB_INDICATORS.values()), wb_rows)
        print("IMF Fiscal Monitor (general government, fiscal years)")
        write_csv(DATA / "fiscal" / "fiscal_from_imf.csv",
                  ["fiscal_year_end", "revenue_pct_gdp", "expenditure_pct_gdp",
                   "balance_pct_gdp", "primary_balance_pct_gdp",
                   "gross_debt_pct_gdp", "revenue_pct_gdp_proj",
                   "expenditure_pct_gdp_proj", "balance_pct_gdp_proj",
                   "primary_balance_pct_gdp_proj", "gross_debt_pct_gdp_proj"],
                  fiscal())
        print("IMF WEO (real GDP growth)")
        write_csv(DATA / "macro" / "growth_from_imf.csv",
                  ["year", "growth_pct", "growth_pct_proj"], growth_imf())
        print("UNDP Human Development Report")
        write_csv(DATA / "world" / "hdi_from_undp.csv", ["year", "hdi"], hdi())
        print("WHO Global Health Observatory")
        write_csv(DATA / "security" / "suicide_from_who.csv",
                  ["year", "suicide_who_per_100k"], suicide())
        print("BIS credit statistics")
        rows, _ = credit()
        write_csv(DATA / "credit" / "credit_from_bis.csv",
                  ["year", "household_debt_pct_gdp", "debt_service_ratio_pct"],
                  rows)
        print("Transparency International CPI")
        write_csv(DATA / "world" / "cpi_from_ti.csv", ["year", "cpi_score"],
                  cpi())
    except FetchError as e:
        print(f"fetch error: {e}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
