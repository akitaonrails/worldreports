#!/usr/bin/env python3
"""Fill the spine slots Statistics Canada would have filled, into sidecars.

Usage:  python3 -I countries/canada/fetch/fetch_spine.py

Statistics Canada's data platform has served an outage page under HTTP 200
since 2026-10-22. The plate spine still asks every country for the same
indicator in the same slot, and rule 11 says a gap is fetched, not left. So
this fetcher goes to the publishers that redistribute Canada's own numbers,
or that publish their own on Canada, and stages them beside the national
files. Each is labelled with who publishes it; none is presented as
Statistics Canada's, and every slot that gets a StatCan line once the
platform returns is listed in HANDOFF.md.

  World Bank WDI   real GDP growth, CPI inflation (both Statistics Canada's
                   figures, redistributed), the migrant share of the
                   population (UN DESA), bank non-performing loans (IMF FSI)
  Federal Reserve  H.10 daily US$/C$ noon buying rate in New York, averaged
                   by year and by month: the one exchange-rate series that
                   covers 2006-07, where the Bank of Canada's noon file
                   begins in May 2007
  Yahoo Finance    S&P/TSX composite and S&P 500, monthly closes
                   (official: false — no official body publishes an index)
  Bank of Canada   Valet: the posted 5-year conventional mortgage rate
                   (weekly) and the rate on new insured and uninsured
                   mortgages, weighted by the funds advanced (monthly, 2013+)
  IMF              GFS expenditure by function (COFOG) and the statement of
                   operations (interest payable), general government; IMTS
                   goods exports and balances by partner
  OECD             minimum wages (provincial, employment-weighted); the
                   Income Distribution Database (Gini, relative poverty);
                   causes of mortality (deaths, crude rates per 100,000 by
                   cause, Statistics Canada's death registrations)
  PHAC             apparent opioid toxicity deaths and their published
                   crude rate per 100,000 (Health Infobase)
  Transparency     Corruption Perceptions Index, 2012-method time series
  International

Every payload is shape-checked BEFORE it is cached, every series is
spot-checked against a value read off the publisher on 2026-10-22, and
nothing is written unless all of them pass. Holes stay blank.
"""
from __future__ import annotations

import csv
import io
import json
import re
import statistics
import sys
import time
import urllib.request
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache" / "spine"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)", "Accept": "*/*"}
SDMX_CSV = "application/vnd.sdmx.data+csv;version=1.0.0"
FIRST, LAST = 2005, 2026


class FetchError(RuntimeError):
    pass


def get(url: str, name: str, check, accept: str | None = None) -> bytes:
    """The body at `url`, validated by `check` before it is cached.

    A cached error page survives the retry that would have fixed it, so the
    check runs on the way in and again on any copy an older run left.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / name
    if path.exists():
        raw = path.read_bytes()
        try:
            check(raw)
            return raw
        except Exception as e:  # noqa: BLE001
            print(f"  stale cache {name}: {e}", file=sys.stderr)
            path.unlink()
    headers = dict(HEADERS)
    if accept:
        headers["Accept"] = accept
    last: Exception | None = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=300) as r:
                raw = r.read()
            check(raw)
            path.write_bytes(raw)
            return raw
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"  {name} attempt {attempt + 1}: {e}", file=sys.stderr)
            time.sleep(3 * (attempt + 1))
    raise FetchError(f"{url}: {last}")


def sdmx_rows(raw: bytes) -> list[dict]:
    return list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))


# ------------------------------------------------------------ World Bank
WB = ("https://api.worldbank.org/v2/country/CAN/indicator/{code}"
      "?format=json&per_page=200&date=2005:2026")


def wb(code: str) -> dict[int, float]:
    def check(raw: bytes) -> None:
        p = json.loads(raw)
        if not (isinstance(p, list) and len(p) == 2 and p[1]):
            raise ValueError("not a World Bank indicator response")
        if p[0].get("pages") != 1:
            raise ValueError("paged response")
        if {r["indicator"]["id"] for r in p[1]} != {code} or \
                {r["countryiso3code"] for r in p[1]} != {"CAN"}:
            raise ValueError("wrong series in payload")

    raw = get(WB.format(code=code), f"wb_{code}.json", check)
    return {int(r["date"]): float(r["value"]) for r in json.loads(raw)[1]
            if r["value"] is not None and FIRST <= int(r["date"]) <= LAST}


# ------------------------------------------------------ Federal Reserve
H10 = "https://www.federalreserve.gov/releases/h10/hist/dat00_ca.htm"
MONTHS = {m: i for i, m in enumerate(
    "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split(), 1)}


def h10() -> dict[tuple[int, int], list[float]]:
    """Daily C$ per US$ from the H.10 historical page, by (year, month).

    The page is one HTML table, a date header cell and a rate cell per
    business day; 'ND' marks a day with no rate and is skipped, not zeroed.
    """
    row = re.compile(r'<th id="r\d+"[^>]*>\s*(\d{1,2})-([A-Z]{3})-(\d{2})\s*'
                     r'</th>\s*<td[^>]*>\s*([\dND.]+)\s*</td>')

    def check(raw: bytes) -> None:
        t = raw.decode("utf-8", "replace")
        if "Canadian" not in t or "H.10" not in t:
            raise ValueError("not the H.10 Canada page")
        if len(row.findall(t)) < 5000:
            raise ValueError("too few daily rows")

    t = get(H10, "fed_h10_canada.htm", check).decode("utf-8", "replace")
    out: dict[tuple[int, int], list[float]] = {}
    for d, mon, yy, v in row.findall(t):
        if v == "ND":
            continue
        y = 2000 + int(yy)
        if FIRST <= y <= LAST:
            out.setdefault((y, MONTHS[mon]), []).append(float(v))
    return out


# ---------------------------------------------------------------- Yahoo
YAHOO = ("https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
         "?period1=1104537600&period2={end}&interval=1mo")


def yahoo_monthly(sym: str) -> dict[tuple[int, int], float]:
    """Monthly closes, keyed (year, month). The running month is a part-
    month and is dropped: its 'close' is today's level, not a month-end."""
    def check(raw: bytes) -> None:
        p = json.loads(raw)["chart"]
        if p.get("error") or not p.get("result"):
            raise ValueError(f"Yahoo error: {p.get('error')}")
        meta = p["result"][0]["meta"]
        if meta.get("symbol") != sym:
            raise ValueError(f"wrong symbol {meta.get('symbol')}")

    end = int(datetime.now(timezone.utc).timestamp())
    tag = sym.replace("^", "")
    raw = get(YAHOO.format(sym=urllib.request.quote(sym), end=end),
              f"yahoo_{tag}_1mo.json", check)
    res = json.loads(raw)["chart"]["result"][0]
    today = date.today()
    out = {}
    for ts, c in zip(res["timestamp"], res["indicators"]["quote"][0]["close"]):
        if c is None:
            continue
        # Yahoo stamps a monthly bar at the exchange's local midnight on the
        # 1st, which is the evening of the last day of the month before in
        # UTC; shifting by a day lands every bar in its own month.
        d = datetime.fromtimestamp(ts + 86400, timezone.utc).date()
        if (d.year, d.month) == (today.year, today.month):
            continue
        if FIRST <= d.year <= LAST:
            out[(d.year, d.month)] = float(c)
    return out


# -------------------------------------------------------- Bank of Canada
VALET = "https://www.bankofcanada.ca/valet/observations/{s}/json"


def valet(series: str) -> dict[str, float]:
    def check(raw: bytes) -> None:
        p = json.loads(raw)
        if series not in p.get("seriesDetail", {}) or not p.get("observations"):
            raise ValueError("not a Valet observations payload")

    raw = get(VALET.format(s=series), f"boc_{series}.json", check)
    out = {}
    for o in json.loads(raw)["observations"]:
        v = (o.get(series) or {}).get("v")
        if v not in (None, ""):
            out[o["d"]] = float(v)
    return out


# ------------------------------------------------------------------ IMF
IMF = "https://api.imf.org/external/sdmx/2.1/data/IMF.STA,{flow}/{key}?startPeriod=2005"


def imf(flow: str, key: str, name: str, need: set[str]) -> list[dict]:
    def check(raw: bytes) -> None:
        rows = sdmx_rows(raw)
        if not rows or not need <= set(rows[0]):
            raise ValueError("not an SDMX-CSV payload")
        if {r["COUNTRY"] for r in rows} != {"CAN"}:
            raise ValueError("payload is for another country")

    return sdmx_rows(get(IMF.format(flow=flow, key=key), name, check, SDMX_CSV))


# ----------------------------------------------------------------- OECD
OECD = ("https://sdmx.oecd.org/public/rest/data/{flow}/{key}"
        "?startPeriod=2005&dimensionAtObservation=AllDimensions")


def oecd(flow: str, key: str, name: str) -> list[dict]:
    def check(raw: bytes) -> None:
        rows = sdmx_rows(raw)
        if not rows or "OBS_VALUE" not in rows[0]:
            raise ValueError(f"not an SDMX-CSV payload: {raw[:80]!r}")
        if {r["REF_AREA"] for r in rows} != {"CAN"}:
            raise ValueError("payload is for another country")

    return sdmx_rows(get(OECD.format(flow=flow, key=key), name, check,
                         SDMX_CSV))


# ----------------------------------------------------------------- PHAC
PHAC = ("https://health-infobase.canada.ca/src/data/substance-related-harms/"
        "download/HealthInfobase-SubstanceHarmsData.zip")


def phac() -> list[dict]:
    def check(raw: bytes) -> None:
        if raw[:2] != b"PK":
            raise ValueError("not a zip")
        z = zipfile.ZipFile(io.BytesIO(raw))
        if "SubstanceHarmsData.csv" not in z.namelist():
            raise ValueError("SubstanceHarmsData.csv missing")

    raw = get(PHAC, "phac_substance_harms.zip", check)
    z = zipfile.ZipFile(io.BytesIO(raw))
    text = z.read("SubstanceHarmsData.csv").decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


# ------------------------------------------------- Transparency Intl.
TI_EDITION = 2025
TI = (f"https://images.transparencycdn.org/images/"
      f"CPI{TI_EDITION}-Results-and-trends.xlsx")


def xlsx_rows(raw: bytes, sheet_name: str) -> list[dict[str, str]]:
    """One sheet of an xlsx as rows of {column letter: text}.

    Read from the XML directly: the TI workbook carries defined names that
    point at sheets openpyxl cannot locate, and it then reports no sheets.
    """
    z = zipfile.ZipFile(io.BytesIO(raw))
    book = z.read("xl/workbook.xml").decode()
    rels = z.read("xl/_rels/workbook.xml.rels").decode()
    sheets = dict(re.findall(r'<sheet [^>]*name="([^"]+)"[^>]*r:id="([^"]+)"',
                             book))
    target = dict(re.findall(r'Id="([^"]+)"[^>]*Target="([^"]+)"', rels)
                  + [(b, a) for a, b in re.findall(
                      r'Target="([^"]+)"[^>]*Id="([^"]+)"', rels)])
    path = "xl/" + target[sheets[sheet_name]].lstrip("/").replace("xl/", "")
    ss = z.read("xl/sharedStrings.xml").decode()
    strings = ["".join(re.findall(r"<t[^>]*>(.*?)</t>", c, re.S))
               for c in re.findall(r"<si>(.*?)</si>", ss, re.S)]
    out = []
    for row in re.findall(r"<row[^>]*>(.*?)</row>", z.read(path).decode(), re.S):
        cells = {}
        for m in re.finditer(r'<c r="([A-Z]+)\d+"([^>]*?)(?:/>|>(.*?)</c>)',
                             row, re.S):
            ref, attrs, body = m.groups()
            v = re.search(r"<v>(.*?)</v>", body or "")
            val = v.group(1) if v else ""
            if 't="s"' in attrs and val:
                val = strings[int(val)]
            cells[ref] = val
        out.append(cells)
    return out


def ti() -> dict[int, float]:
    sheet = "CPI Historical"

    def check(raw: bytes) -> None:
        if raw[:2] != b"PK":
            raise ValueError("not a workbook (TI's CDN answers 403 with HTML)")
        rows = xlsx_rows(raw, sheet)
        if not any(r.get("A") == "Canada" for r in rows):
            raise ValueError("no Canada rows")

    raw = get(TI, f"ti_CPI{TI_EDITION}.xlsx", check)
    rows = xlsx_rows(raw, sheet)
    head = next(r for r in rows if r.get("A", "").startswith("Country"))
    col = {v: k for k, v in head.items()}
    out = {}
    for r in rows:
        if r.get(col["ISO3"]) == "CAN" and r.get(col["CPI score"]):
            out[int(r[col["Year"]])] = float(r[col["CPI score"]])
    return out


# ------------------------------------------------------------ assembly
def annual_mean(by_month: dict[tuple[int, int], float]) -> dict[int, tuple]:
    years: dict[int, list[float]] = {}
    for (y, _m), v in by_month.items():
        years.setdefault(y, []).append(v)
    return {y: (statistics.fmean(v), len(v)) for y, v in years.items()}


def collect() -> dict[str, tuple[list[str], dict[int, dict]]]:
    out: dict[str, tuple[list[str], dict[int, dict]]] = {}

    def put(rel, cols, rows):
        if not rows:
            raise FetchError(f"{rel}: empty")
        out[rel] = (cols, rows)

    print("World Bank")
    g, cpi = wb("NY.GDP.MKTP.KD.ZG"), wb("FP.CPI.TOTL.ZG")
    put("macro/growth_prices_from_wb.csv", ["real_growth_pct", "cpi_inflation_pct"],
        {y: {"real_growth_pct": round(g[y], 2) if y in g else "",
             "cpi_inflation_pct": round(cpi[y], 2) if y in cpi else ""}
         for y in sorted(set(g) | set(cpi))})
    ms = wb("SM.POP.TOTL.ZS")
    put("social/migrant_stock_from_wb.csv", ["migrant_share_pct"],
        {y: {"migrant_share_pct": ms[y]} for y in sorted(ms)})
    npl = wb("FB.AST.NPER.ZS")
    put("credit/npl_from_wb.csv", ["npl_pct"],
        {y: {"npl_pct": round(npl[y], 2)} for y in sorted(npl)})

    print("Federal Reserve H.10")
    days = h10()
    fx_month = {k: statistics.fmean(v) for k, v in days.items()}
    fx_year: dict[int, list[float]] = {}
    for (y, _m), v in days.items():
        fx_year.setdefault(y, []).extend(v)
    put("markets/usdcad_from_fed.csv", ["cad_per_usd_avg", "days", "months"],
        {y: {"cad_per_usd_avg": round(statistics.fmean(v), 4), "days": len(v),
             "months": len({m for (yy, m) in days if yy == y})}
         for y, v in sorted(fx_year.items())})

    print("Yahoo Finance")
    tsx, spx = yahoo_monthly("^GSPTSE"), yahoo_monthly("^GSPC")
    # The TSX in US$, month by month: each month's close over that month's
    # average H.10 rate. A month without an H.10 rate is left out rather
    # than converted at a neighbour's.
    tsx_usd = {k: v / fx_month[k] for k, v in tsx.items() if k in fx_month}
    a_tsx, a_usd, a_spx = (annual_mean(tsx), annual_mean(tsx_usd),
                           annual_mean(spx))
    put("markets/equities_from_yahoo.csv",
        ["tsx_cad_avg", "tsx_usd_avg", "spx_usd_avg", "months"],
        {y: {"tsx_cad_avg": round(a_tsx[y][0], 2),
             "tsx_usd_avg": round(a_usd[y][0], 2),
             "spx_usd_avg": round(a_spx[y][0], 2),
             "months": min(a_tsx[y][1], a_usd[y][1], a_spx[y][1])}
         for y in sorted(set(a_tsx) & set(a_usd) & set(a_spx))})

    print("Bank of Canada")
    posted = valet("V80691335")
    p_year: dict[int, list[float]] = {}
    for d, v in posted.items():
        y = int(d[:4])
        if FIRST <= y <= LAST:
            p_year.setdefault(y, []).append(v)
    ins_r, unins_r = valet("V122667775"), valet("V122667781")
    ins_f, unins_f = valet("V122667724"), valet("V122667730")
    num: dict[int, float] = {}
    den: dict[int, float] = {}
    months: dict[int, int] = {}
    for d in sorted(set(ins_r) & set(unins_r) & set(ins_f) & set(unins_f)):
        y = int(d[:4])
        num[y] = num.get(y, 0) + ins_r[d] * ins_f[d] + unins_r[d] * unins_f[d]
        den[y] = den.get(y, 0) + ins_f[d] + unins_f[d]
        months[y] = months.get(y, 0) + 1
    put("credit/mortgage_rates_from_boc.csv",
        ["posted_5y_avg", "new_mortgage_rate", "new_mortgage_months"],
        {y: {"posted_5y_avg": round(statistics.fmean(p_year[y]), 2)
             if y in p_year else "",
             "new_mortgage_rate": round(num[y] / den[y], 2) if y in den else "",
             "new_mortgage_months": months.get(y, "")}
         for y in sorted(set(p_year) | set(den))})

    print("IMF — GFS and IMTS")
    need = {"COUNTRY", "SECTOR", "INDICATOR", "TYPE_OF_TRANSFORMATION",
            "TIME_PERIOD", "OBS_VALUE"}
    cofog = imf("GFS_COFOG", "CAN.S13....A", "imf_gfs_cofog.csv", need)
    divisions = [("TOTOUT_T", "total"), ("GF10_T", "social_protection"),
                 ("GF07_T", "health"), ("GF09_T", "education"),
                 ("GF01_T", "general_public_services"),
                 ("GF04_T", "economic_affairs"), ("GF02_T", "defence"),
                 ("GF03_T", "public_order"), ("GF05_T", "environment"),
                 ("GF06_T", "housing"), ("GF08_T", "recreation_culture")]
    rows: dict[int, dict] = {}
    for r in cofog:
        if (r["SECTOR"] == "S13" and r["TYPE_OF_TRANSFORMATION"] == "POGDP_PT"
                and r["OBS_VALUE"]):
            name = dict(divisions).get(r["INDICATOR"])
            if name:
                rows.setdefault(int(r["TIME_PERIOD"]), {})[name] = round(
                    float(r["OBS_VALUE"]), 2)
    for y, r in rows.items():
        parts = sum(v for k, v in r.items() if k != "total")
        if abs(parts - r["total"]) > 0.1:
            raise FetchError(f"COFOG {y}: divisions sum {parts} vs {r['total']}")
    put("fiscal/cofog_from_imf.csv", [n for _, n in divisions], rows)

    soo = imf("GFS_SOO", "CAN.S13....A", "imf_gfs_soo.csv", need)
    pick = {"G24_T": "interest_payable", "G1_T": "revenue",
            "G2M_T": "expenditure", "GNLB_T": "net_lending"}
    rows = {}
    for r in soo:
        if (r["SECTOR"] == "S13" and r["TYPE_OF_TRANSFORMATION"] == "POGDP_PT"
                and r["INDICATOR"] in pick and r["OBS_VALUE"]):
            rows.setdefault(int(r["TIME_PERIOD"]), {})[pick[r["INDICATOR"]]] = \
                round(float(r["OBS_VALUE"]), 2)
    put("fiscal/gfs_operations_from_imf.csv", list(pick.values()), rows)

    imts = imf("IMTS", "CAN.XG_FOB_USD+TBG_USD..A", "imf_imts.csv",
               {"COUNTRY", "INDICATOR", "COUNTERPART_COUNTRY", "TIME_PERIOD",
                "OBS_VALUE"})
    x: dict[str, dict[int, float]] = {}
    b: dict[str, dict[int, float]] = {}
    for r in imts:
        if not r["OBS_VALUE"]:
            continue
        tgt = x if r["INDICATOR"] == "XG_FOB_USD" else b
        tgt.setdefault(r["COUNTERPART_COUNTRY"], {})[int(r["TIME_PERIOD"])] = \
            float(r["OBS_VALUE"])
    world = x["G001"]
    last = max(y for y in world if y <= LAST - 1)
    # Ranked once, on the last full year, among real countries (ISO3
    # alphabetic codes; the G/T codes are regional aggregates).
    ranked = sorted((c for c in x if re.fullmatch(r"[A-Z]{3}", c)
                     and last in x[c]), key=lambda c: -x[c][last])[:6]
    cols = (["exports_world_usd"] + [f"exports_{c.lower()}_usd" for c in ranked]
            + ["balance_world_usd", "balance_usa_usd"])
    rows = {}
    for y in sorted(world):
        rows[y] = {"exports_world_usd": round(world[y])}
        for c in ranked:
            if y in x[c]:
                rows[y][f"exports_{c.lower()}_usd"] = round(x[c][y])
        if y in b.get("G001", {}):
            rows[y]["balance_world_usd"] = round(b["G001"][y])
        if y in b.get("USA", {}):
            rows[y]["balance_usa_usd"] = round(b["USA"][y])
    put("trade/partners_from_imf.csv", cols, rows)

    print("OECD")
    mw = oecd("OECD.ELS.SAE,DSD_EARNINGS@MW_CURP,", "CAN......",
              "oecd_mw_curp.csv")
    rows = {}
    for r in mw:
        if r["UNIT_MEASURE"] == "CAD" and r["OBS_VALUE"]:
            k = {"H": "hourly_cad", "A": "annual_cad"}.get(r["PAY_PERIOD"])
            if k:
                rows.setdefault(int(r["TIME_PERIOD"]), {})[k] = float(r["OBS_VALUE"])
    put("social/minimum_wage_from_oecd.csv", ["hourly_cad", "annual_cad"], rows)

    idd = oecd("OECD.WISE.INE,DSD_WISE_IDD@DF_IDD,", "CAN.A........",
               "oecd_idd.csv")
    want = {("INC_DISP_GINI", "_T", "_Z"): "gini",
            ("PR_INC_DISP", "_T", "PL_50"): "poverty_50_pct",
            ("PR_INC_DISP", "Y_LT18", "PL_50"): "child_poverty_50_pct",
            ("PR_INC_DISP", "Y_GT65", "PL_50"): "old_age_poverty_50_pct"}
    rows = {}
    for r in idd:
        k = want.get((r["MEASURE"], r["AGE"], r["POVERTY_LINE"]))
        # One income definition throughout: the 2012 one, which the OECD
        # carries back to 2005 for Canada. The 2011 definition stops in 2011
        # and would be a seam.
        if k and r["METHODOLOGY"] == "METH2012" and r["OBS_VALUE"]:
            rows.setdefault(int(r["TIME_PERIOD"]), {})[k] = round(
                float(r["OBS_VALUE"]), 3 if k == "gini" else 1)
    put("social/income_from_oecd.csv", list(want.values()), rows)

    com = oecd("OECD.ELS.HD,DSD_HEALTH_STAT@DF_COM,", "CAN............",
               "oecd_com.csv")
    causes = {"_T": "all_causes", "CICDCVID": "covid19",
              "CICDNEOP": "cancer", "CICDCIRC": "circulatory",
              "CICDHARM": "self_harm", "CICDTRAC": "transport",
              "CICDPOSN": "accidental_poisoning"}
    rows = {}
    for r in com:
        if r["SEX"] != "_T" or not r["OBS_VALUE"] or r["DEATH_CAUSE"] not in causes:
            continue
        y, c = int(r["TIME_PERIOD"]), causes[r["DEATH_CAUSE"]]
        if r["UNIT_MEASURE"] == "DT" and c == "all_causes":
            rows.setdefault(y, {})["deaths"] = int(float(r["OBS_VALUE"]))
        elif r["UNIT_MEASURE"] == "DT_10P5HB" and r["CALC_METHODOLOGY"] == "CRUDE":
            rows.setdefault(y, {})[f"{c}_per_100k"] = float(r["OBS_VALUE"])
    put("social/causes_of_death_from_oecd.csv",
        ["deaths"] + [f"{c}_per_100k" for c in causes.values()], rows)

    print("PHAC")
    rows = {}
    for r in phac():
        if (r["Substance"] == "Opioids" and r["Source"] == "Deaths"
                and r["Region"] == "Canada" and r["Time_Period"] == "By year"
                and r["Specific_Measure"] == "Overall numbers"
                and re.fullmatch(r"\d{4}", r["Year_Quarter"])):
            k = {"Number": "deaths", "Crude rate": "rate_per_100k"}.get(r["Unit"])
            if k:
                rows.setdefault(int(r["Year_Quarter"]), {})[k] = float(r["Value"])
    put("social/opioids_from_phac.csv", ["deaths", "rate_per_100k"], rows)

    print("Transparency International")
    cpi_ti = ti()
    put("international/cpi_from_ti.csv", ["cpi_score"],
        {y: {"cpi_score": v} for y, v in sorted(cpi_ti.items())})
    return out


# (sidecar, column, year, value) read off the publishers on 2026-10-22.
SPOT = [
    ("macro/growth_prices_from_wb.csv", "real_growth_pct", 2009, -2.92),
    ("macro/growth_prices_from_wb.csv", "cpi_inflation_pct", 2022, 6.8),
    ("social/migrant_stock_from_wb.csv", "migrant_share_pct", 2020, 21.8),
    ("credit/npl_from_wb.csv", "npl_pct", 2024, 0.57),
    ("markets/usdcad_from_fed.csv", "cad_per_usd_avg", 2006, None),
    ("credit/mortgage_rates_from_boc.csv", "posted_5y_avg", 2006, None),
    ("fiscal/cofog_from_imf.csv", "social_protection", 2024, 12.19),
    ("fiscal/gfs_operations_from_imf.csv", "interest_payable", 2024, 3.51),
    ("social/minimum_wage_from_oecd.csv", "annual_cad", 2025, 34465.6),
    ("social/income_from_oecd.csv", "child_poverty_50_pct", 2019, 10.9),
    ("social/causes_of_death_from_oecd.csv", "deaths", 2022, 338217),
    ("social/causes_of_death_from_oecd.csv", "covid19_per_100k", 2022, 51.2),
    ("social/opioids_from_phac.csv", "deaths", 2023, 8083),
    ("social/opioids_from_phac.csv", "rate_per_100k", 2023, 20.2),
    ("international/cpi_from_ti.csv", "cpi_score", 2012, 84),
]


def spot(tables) -> None:
    for rel, col, year, want in SPOT:
        got = tables[rel][1].get(year, {}).get(col, "")
        if got == "":
            raise FetchError(f"{rel}: {col} {year} missing")
        if want is not None and abs(float(got) - want) > 0.011 * max(1, abs(want)) \
                and abs(float(got) - want) > 0.01:
            raise FetchError(f"{rel}: {col} {year} = {got}, expected {want}")
    # Cross-checks: the H.10 average against the Bank of Canada's own
    # single daily rate, and the OECD death count against the World Bank
    # crude death rate times the World Bank population.
    fed = tables["markets/usdcad_from_fed.csv"][1]
    boc = {}
    with (DATA / "markets/usdcad.csv").open() as fh:
        for r in csv.DictReader(ln for ln in fh if not ln.startswith("#")):
            if r["usd_cad_daily_avg"]:
                boc[int(r["year"])] = float(r["usd_cad_daily_avg"])
    for y in (2018, 2022, 2024):
        gap = abs(fed[y]["cad_per_usd_avg"] - boc[y]) / boc[y]
        print(f"  H.10 vs BoC daily {y}: {fed[y]['cad_per_usd_avg']} vs {boc[y]}"
              f" ({gap:.2%})")
        if gap > 0.005:
            raise FetchError(f"H.10 and the Bank of Canada differ by {gap:.2%}")


def write(tables) -> None:
    for rel, (cols, rows) in tables.items():
        path = DATA / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["year"] + cols)
            for y in sorted(rows):
                if FIRST <= y <= LAST:
                    w.writerow([y] + [rows[y].get(c, "") for c in cols])
        print(f"  data/{rel}  {len(rows)} rows")


def main() -> None:
    tables = collect()
    spot(tables)
    write(tables)
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
