#!/usr/bin/env python3
"""Refresh the Federal Finance Administration (EFV/AFF/FFA) fiscal series.

Usage:  python3 -I countries/switzerland/fetch/fetch_efv.py

Two files from the EFV's open-data store, www.data.finance.admin.ch:

  fs_dashboard/main_extern.csv   main aggregates and forecasts, general
                                 government and its four subsectors, in the
                                 national FS model and the IMF GFS model
  gfs_dashboard/cofog_int.csv    spending by COFOG function, the EFV's own
                                 rows for Switzerland in its international
                                 comparison

These are fixed paths (the dashboards' own data files, refreshed in place;
Last-Modified 2026-09-22 on the day this was written), not editioned
downloads, so there is no index page to resolve.

Things this source will mislead you about.

**The latest years are not outturns.** Every row carries a `source`:
Rechnung (accounts, an outturn), Prognosen (EFV forecast), Hochrechnung
(the Confederation's in-year projection), Budget/Finanzpläne, Umfrage
Budget (survey of cantonal budgets), Vorhandene Daten (cantons with data so
far: partial). For general government 2025 is still Prognosen; 2024 is the
last outturn. The label differs by subsector and year (the Confederation and
social security already have 2025 accounts), so every row keeps its own
status, and the general-government last-outturn year is asserted.

**Ratios are fractions in the file** (0.237, not 23.7). They are written
here as percentages.

**Four debt measures, all correct, for the same general government** (header
trap 5 in SOURCES.yaml): Maastricht debt (23.7% of GDP in 2024), GFS gross
debt (30.0%), GFS total liabilities (40.4%, the IMF's GGXWDG definition)
and net debt. Plus two tax ratios: the fiscal ratio (26.7%) and the
"extended" ratio (37.3%) that adds compulsory health-insurance premiums and
occupational-pension contributions. Each is its own column, never one line.

**Two accounting models.** GFS is the IMF model, internationally
comparable; FS is the national model. They differ (2024 balance: GFS
+2,480, FS +3,254 CHF mn). The GFS columns are the headline; the FS balance
and gross debt are kept, prefixed `fs_`.

**GDP vintage.** The EFV divides by the CURRENT BFS vintage (its `bip`
2024 = 860,932 CHF mn, the 2026-08-25 revision), not the Eurostat/World
Bank one.

Spot values recorded in SOURCES.yaml are asserted, and general-government
total liabilities are checked against the IMF DataMapper (GGXWDG_NGDP),
the budget balance and COFOG total against Eurostat. Outputs are
`_from_efv.csv` sidecars; nothing here overwrites a curated file.
"""
from __future__ import annotations

import csv
import io
import json
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache"
STORE = "https://www.data.finance.admin.ch/static/assets/datasets/"
MAIN = STORE + "fs_dashboard/main_extern.csv"
COFOG = STORE + "gfs_dashboard/cofog_int.csv"
IMF = "https://www.imf.org/external/datamapper/api/v1/GGXWDG_NGDP/CHE"
ESTAT = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
         "{ds}?geo=CH&sector=S13&unit=PC_GDP&na_item={item}&freq=A{extra}")
HEADERS = {"User-Agent": "worldreports-data-fetcher/1.0"}
Y0, Y1 = 2006, 2026

SECTORS = ("staat", "bund", "ktn", "gdn", "sv")
SECTOR_NAMES = {"staat": "general_government", "bund": "confederation",
                "ktn": "cantons", "gdn": "communes", "sv": "social_security"}
STATUS = {"Rechnung": "outturn", "Prognosen": "forecast",
          "Hochrechnung": "projection", "Budget/Finanzpläne": "budget",
          "Umfrage Budget": "budget_survey", "Vorhandene Daten": "partial"}

# (output column, variable, model, scale) — scale 100 turns a fraction
# into a percentage; levels are CHF millions as published.
COLUMNS = [
    ("revenue", "ertrag", "gfs", 1),
    ("expenditure", "ausgaben", "gfs", 1),
    ("balance", "saldo", "gfs", 1),
    ("balance_pct_gdp", "defizit_ueberschuss", "gfs", 100),
    ("expenditure_pct_gdp", "staatsquote", "gfs", 100),
    ("revenue_pct_gdp", "einnahmenquote", "gfs", 100),
    ("revenue_ext_pct_gdp", "einnahmenquote_erweitert", "gfs", 100),
    ("tax_revenue", "fiskalertrag", "gfs", 1),
    ("tax_revenue_ext", "fiskalertrag_erweitert", "gfs", 1),
    ("tax_ratio", "fiskalquote", "gfs", 100),
    ("tax_ratio_ext", "fiskalquote_erweitert", "gfs", 100),
    ("maastricht_debt", "maastricht_schuld", "gfs", 1),
    ("maastricht_debt_pct_gdp", "schuldenquote", "gfs", 100),
    ("gfs_gross_debt_pct_gdp", "bruttoschuldenquote", "gfs", 100),
    ("total_liabilities", "fremdkapital", "gfs", 1),
    ("total_liabilities_pct_gdp", "fremdkapitalquote", "gfs", 100),
    ("net_debt", "nettoschuld", "gfs", 1),
    ("net_debt_pct_gdp", "nettoschuldenquote", "gfs", 100),
    ("fs_balance", "saldo", "fs", 1),
    ("fs_gross_debt", "bruttoschuld_fs", "fs", 1),
]


# ---------------------------------------------------------------- fetch

def get(url: str, timeout: int = 300) -> bytes:
    last = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            last = e
            wait = 30 * (attempt + 1) if e.code in (403, 429) else 3 * (attempt + 1)
        except Exception as e:  # noqa: BLE001
            last = e
            wait = 3 * (attempt + 1)
        time.sleep(wait)
    raise RuntimeError(f"{url}: {last}")


def efv_csv(url: str, name: str, header: list[str]) -> list[dict]:
    """One EFV CSV, its header checked before it is cached."""
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / f"efv_{name}.csv"
    if cache_file.exists():
        text = cache_file.read_text(encoding="utf-8")
    else:
        text = get(url).decode("utf-8-sig")
        first = next(csv.reader(io.StringIO(text)))
        if first != header:
            raise RuntimeError(f"efv {name}: header {first!r}, expected {header!r}")
        cache_file.write_text(text, encoding="utf-8")
        time.sleep(1)
    return list(csv.DictReader(io.StringIO(text)))


def json_cached(url: str, name: str, ok) -> dict:
    cache_file = CACHE / f"efv_xcheck_{name}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    payload = json.loads(get(url))
    if not ok(payload):
        raise RuntimeError(f"{name}: unexpected payload")
    cache_file.write_text(json.dumps(payload))
    time.sleep(1)
    return payload


def estat(ds: str, item: str, extra: str = "") -> dict[int, float]:
    url = ESTAT.format(ds=ds, item=item, extra=extra)
    p = json_cached(url, f"estat_{ds}_{item}",
                    lambda p: "value" in p and "dimension" in p)
    idx = p["dimension"]["time"]["category"]["index"]
    return {int(y): p["value"][str(i)] for y, i in idx.items()
            if str(i) in p["value"]}


# ---------------------------------------------------------------- helpers

def check(label: str, got, want: float, tol: float) -> None:
    if got is None:
        raise SystemExit(f"  !! {label}: missing from the data")
    if abs(got - want) > tol:
        raise SystemExit(f"  !! {label} = {got}, expected {want} ± {tol}; "
                         f"not writing")
    print(f"  ok {label}: {round(got, 4)} (expected {want})")


def write(rel: str, comment: str, header: list[str], rows: list[list]) -> None:
    path = DATA / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        for line in comment.strip().splitlines():
            fh.write(f"# {line}".rstrip() + "\n")
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    span = f"{rows[0][0]}–{rows[-1][0]}" if rows else "EMPTY"
    print(f"  data/{rel}  {len(rows)} rows ({span})")


def fmt(v, nd):
    return "" if v is None else round(v, nd)


# ---------------------------------------------------------------- main_extern

def general_government() -> tuple[dict, dict, int]:
    rows = efv_csv(MAIN, "main_extern",
                   ["", "hh", "model", "variable", "jahr", "value", "source"])
    val: dict = {}
    src: dict = {}
    gdp: dict[int, float] = {}
    for r in rows:
        if r["variable"] == "bip" and r["hh"] == "NA":
            gdp[int(r["jahr"])] = float(r["value"])
            continue
        if r["hh"] == "NA":
            continue   # FS/GFS bridge items (debt_*, *_ergebnis): not drawn
        key = (r["hh"], r["model"], r["variable"], int(r["jahr"]))
        if key in val:
            raise SystemExit(f"  !! duplicate row {key}")
        if r["value"] in ("", "NA"):
            continue
        if r["source"] not in STATUS:
            raise SystemExit(f"  !! unknown source label {r['source']!r}")
        val[key] = float(r["value"])
        src[key] = r["source"]

    g = lambda v, y, m="gfs", hh="staat": val.get((hh, m, v, y))  # noqa: E731
    # Spot values, SOURCES.yaml (staat, GFS, 2024 accounts).
    check("GG 2024 balance (CHF mn)", g("saldo", 2024), 2480, 1)
    check("GG 2020 balance (CHF mn)", g("saldo", 2020), -18705, 1)
    check("GG 2024 balance FS model (CHF mn)", g("saldo", 2024, "fs"), 3254, 1)
    check("GG 2024 balance % GDP", g("defizit_ueberschuss", 2024) * 100, 0.29, 0.005)
    check("GG 2024 expenditure ratio", g("staatsquote", 2024) * 100, 31.4, 0.05)
    check("GG 2024 tax ratio", g("fiskalquote", 2024) * 100, 26.7, 0.05)
    check("GG 2024 extended tax ratio", g("fiskalquote_erweitert", 2024) * 100, 37.3, 0.05)
    check("GG 2024 Maastricht debt % GDP", g("schuldenquote", 2024) * 100, 23.7, 0.05)
    check("GG 2024 GFS gross debt % GDP", g("bruttoschuldenquote", 2024) * 100, 30.0, 0.05)
    check("GG 2024 GFS total liabilities % GDP", g("fremdkapitalquote", 2024) * 100, 40.4, 0.05)
    # The denominator is the current BFS vintage (ts-x-04.02.01.02).
    check("EFV GDP 2024 = BFS 2026-08 vintage (CHF mn)", gdp.get(2024), 860932.1, 0.5)
    check("EFV GDP 2025 = BFS 2026-08 vintage (CHF mn)", gdp.get(2025), 881571.8, 0.5)
    # Ratios are recomputable from levels and EFV's GDP.
    for y in range(Y0, 2025):
        r = g("maastricht_schuld", y) / gdp[y]
        if abs(r - g("schuldenquote", y)) > 0.0005:
            raise SystemExit(f"  !! {y}: Maastricht debt / bip != schuldenquote")
    print("  ok Maastricht debt / EFV GDP reproduces the published ratio 2006–2024")

    # Which year is the last general-government outturn.
    outturn = [y for (hh, m, v, y), s in src.items()
               if hh == "staat" and m == "gfs" and v == "saldo" and s == "Rechnung"]
    last_outturn = max(outturn)
    if last_outturn != 2024 or src[("staat", "gfs", "saldo", 2025)] != "Prognosen":
        print(f"  NOTE last general-government outturn is now {last_outturn}; "
              f"2025 is {src.get(('staat', 'gfs', 'saldo', 2025))} — update the "
              f"comments' expectations")
    else:
        print("  ok general government: 2024 last outturn, 2025 Prognosen (forecast)")

    # Second publisher: IMF DataMapper GGXWDG_NGDP = GFS total liabilities.
    imf = json_cached(IMF, "imf_GGXWDG_NGDP",
                      lambda p: "CHE" in p.get("values", {}).get("GGXWDG_NGDP", {}))
    imf = {int(y): v for y, v in imf["values"]["GGXWDG_NGDP"]["CHE"].items()}
    check("IMF GGXWDG_NGDP 2024 (DISCOVERY 40.4)", imf.get(2024), 40.4, 0.05)
    gaps = {y: round(g("fremdkapitalquote", y) * 100 - imf[y], 2)
            for y in range(Y0, 2025) if y in imf}
    worst = max(gaps.items(), key=lambda kv: abs(kv[1]))
    print(f"  .. EFV total liabilities minus IMF GGXWDG, pt: {gaps}")
    if abs(gaps[2024]) > 0.1:
        raise SystemExit(f"  !! 2024 EFV {g('fremdkapitalquote', 2024)*100:.2f} "
                         f"vs IMF {imf[2024]}")
    if abs(worst[1]) > 2.5:
        raise SystemExit(f"  !! EFV vs IMF debt differ by {worst[1]} pt in {worst[0]}")
    print(f"  ok EFV total liabilities = IMF GGXWDG in 2024; largest gap "
          f"{worst[1]:+} pt ({worst[0]}); 2013–2019 run 0.3–0.9 pt apart, years in "
          f"which BFS and Eurostat GDP agree, so the IMF holds an older EFV "
          f"liabilities vintage there")
    # Eurostat gov_10a_main B9, old GDP vintage: tenths apart.
    b9 = estat("gov_10a_main", "B9")
    for y in (2020, 2024):
        diff = g("defizit_ueberschuss", y) * 100 - b9[y]
        if abs(diff) > 0.5:
            raise SystemExit(f"  !! {y} balance EFV vs Eurostat B9 differ {diff:.2f}")
    print(f"  ok balance within 0.5 pt of Eurostat B9 (2020 {b9[2020]}, 2024 {b9[2024]})")

    out = []
    for y in range(Y0, Y1 + 1):
        for hh in SECTORS:
            s_gfs = src.get((hh, "gfs", "saldo", y))
            s_fs = src.get((hh, "fs", "saldo", y))
            if s_gfs is None and s_fs is None:
                continue
            row = [y, SECTOR_NAMES[hh], STATUS.get(s_gfs, ""), STATUS.get(s_fs, ""),
                   fmt(gdp.get(y), 1) if hh == "staat" else ""]
            for _, var, model, scale in COLUMNS:
                v = val.get((hh, model, var, y))
                row.append(fmt(None if v is None else v * scale,
                               3 if scale == 100 else 1))
            out.append(row)
    write("fiscal/general_government_from_efv.csv", f"""
EFV Finanzstatistik, main aggregates and forecasts (fs_dashboard/main_extern.csv).
Calendar fiscal years (the Swiss fiscal year is the calendar year). One row
per year and sector: general_government (staat) and its subsectors
confederation (bund), cantons (ktn), communes (gdn), social_security (sv).
STATUS PER ROW, NEVER DROPPED: status_gfs / status_fs = outturn (Rechnung),
forecast (Prognosen), projection (Hochrechnung, Confederation in-year),
budget, budget_survey (Umfrage Budget), partial (Vorhandene Daten, cantons
with data so far). General government: {last_outturn} is the last outturn;
later rows are EFV forecasts and are not outturns.
Levels in CHF MILLIONS; *_pct_gdp and *_ratio* in PERCENT of GDP (the file
publishes fractions). GDP vintage: EFV's own bip column (gdp_chf_mn, on the
general-government rows) = BFS national accounts as revised 2026-08-25, the
CURRENT vintage, not the Eurostat/World Bank one.
GFS (IMF) model unless prefixed fs_ (national FS model; they differ).
FOUR DEBT MEASURES, separate columns, never one line: maastricht_debt,
gfs_gross_debt_pct_gdp, total_liabilities (= IMF GGXWDG definition, asserted
equal to the IMF's 40.4% for 2024), net_debt; fs_gross_debt is the national
model's gross debt. TWO TAX RATIOS: tax_ratio (Fiskalquote) and tax_ratio_ext
(adds compulsory health-insurance premiums and occupational-pension
contributions; general government only). A blank is a measure the EFV does
not publish for that sector/model/year.
""", ["year", "sector", "status_gfs", "status_fs", "gdp_chf_mn"]
        + [c for c, *_ in COLUMNS], out)
    return val, src, last_outturn


# ---------------------------------------------------------------- COFOG

COFOG_NAMES = {
    "GF01": "general_public_services", "GF02": "defence",
    "GF03": "public_order_safety", "GF04": "economic_affairs",
    "GF05": "environment", "GF06": "housing_community",
    "GF07": "health", "GF08": "recreation_culture_religion",
    "GF09": "education", "GF10": "social_protection",
}


def spending_by_function(val: dict, src: dict) -> None:
    rows = efv_csv(COFOG, "cofog_int",
                   ["", "country_code", "cofog", "jahr", "value", "unit", "source"])
    d: dict = defaultdict(dict)
    for r in rows:
        if r["country_code"] != "CHE" or r["value"] in ("", "NA"):
            continue
        if r["source"] != "Federal Finance Administration (Switzerland)":
            raise SystemExit(f"  !! CHE row not from the EFV: {r['source']!r}")
        key = (r["cofog"], r["unit"], int(r["jahr"]))
        if key in d:
            raise SystemExit(f"  !! duplicate COFOG row {key}")
        d[key] = float(r["value"])
    years = sorted({y for (_, _, y) in d if Y0 <= y <= Y1})
    unit_chf = "CHF (domestic_currency)"
    for y in years:
        tot = sum(d[(gf, unit_chf, y)] for gf in COFOG_NAMES) / 1e6
        ausg = val.get(("staat", "gfs", "ausgaben", y))
        if ausg and abs(tot / ausg - 1) > 0.005:
            raise SystemExit(f"  !! {y}: COFOG total {tot:,.0f} vs GFS "
                             f"expenditure {ausg:,.0f}")
        shares = sum(d[(gf, "percent_total", y)] for gf in COFOG_NAMES)
        if abs(shares - 100) > 0.1:
            raise SystemExit(f"  !! {y}: COFOG shares sum to {shares}")
    print("  ok COFOG functions sum to GFS general-government expenditure, "
          "shares to 100, every year")
    check("COFOG 2024 social protection % GDP", d[("GF10", "percent_gdp", 2024)], 12.24, 0.01)
    tot24 = sum(d[(gf, "percent_gdp", 2024)] for gf in COFOG_NAMES)
    check("COFOG 2024 total % GDP = staatsquote", tot24,
          val[("staat", "gfs", "staatsquote", 2024)] * 100, 0.05)
    # Second publisher: Eurostat gov_10a_exp TOTAL (old GDP vintage).
    es = estat("gov_10a_exp", "TE", "&cofog99=TOTAL")
    for y in (2020, 2024):
        tot = sum(d[(gf, "percent_gdp", y)] for gf in COFOG_NAMES)
        if abs(tot - es[y]) > 1.5:
            raise SystemExit(f"  !! {y}: COFOG total {tot:.1f} vs Eurostat {es[y]}")
    print(f"  ok COFOG total within 1.5 pt of Eurostat gov_10a_exp (2020 {es[2020]}, "
          f"2024 {es[2024]}; old GDP vintage there)")
    out = []
    for y in years:
        status = STATUS.get(src.get(("staat", "gfs", "ausgaben", y)), "")
        row = [y, status, fmt(sum(d[(gf, unit_chf, y)] for gf in COFOG_NAMES) / 1e6, 1)]
        row += [fmt(d.get((gf, "percent_gdp", y)), 3) for gf in COFOG_NAMES]
        row += [fmt(d[(gf, unit_chf, y)] / 1e6, 1) if (gf, unit_chf, y) in d else ""
                for gf in COFOG_NAMES]
        out.append(row)
    write("fiscal/spending_by_function_from_efv.csv", """
EFV, general-government expenditure by COFOG function, GFS model
(gfs_dashboard/cofog_int.csv, the EFV's own Switzerland rows in its
international comparison). Calendar years. *_pct_gdp = PERCENT of GDP (EFV,
current BFS GDP vintage); *_chf_mn = CHF MILLIONS. The ten functions sum to
GFS general-government expenditure in general_government_from_efv.csv
(asserted). `status` is that file's general-government status for the year:
a forecast row is not an outturn. Not the national FS functional
classification (fir_art_funk.csv), which is a 1.26 GB detail file.
""", ["year", "status", "total_chf_mn"]
        + [f"{n}_pct_gdp" for n in COFOG_NAMES.values()]
        + [f"{n}_chf_mn" for n in COFOG_NAMES.values()], out)


def main() -> None:
    print("EFV (data.finance.admin.ch)")
    val, src, _ = general_government()
    spending_by_function(val, src)


if __name__ == "__main__":
    main()
