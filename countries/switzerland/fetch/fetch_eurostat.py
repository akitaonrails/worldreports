#!/usr/bin/env python3
"""Refresh the Eurostat-backed series for Switzerland into sidecar CSVs.

Usage:  python3 -I countries/switzerland/fetch/fetch_eurostat.py

Switzerland is not an EU member, but as an EFTA state it transmits its
national accounts, government finance statistics, HICP, LFS, SILC,
demography, causes of death, police-recorded crime, financial accounts and
the whole migration suite to Eurostat under the bilateral statistical
agreement. BFS, the SNB, EFV and SEM are the primary publishers; every file
written here is the harmonised twin, kept beside the national series and
never spliced into it.

Output goes to `*_from_estat.csv` sidecars under data/, never over a
curated file. Raw cubes are cached under cache/estat_*.json.

THE VINTAGE TRAP (SOURCES.yaml header, trap 1). BFS revised the annual
national accounts on 2026-08-25; Eurostat still carries the PREVIOUS BFS
vintage for 2023 onward (equal to BFS to the decimal through 2022;
2024: CHF 854.0bn here vs 860.9bn at BFS). Every
ratio to GDP in this file set — the government ratios, the tax burden,
COFOG, household debt — is computed by Eurostat on that OLD denominator.
Each CSV's comment says so. Never divide a BFS numerator by the Eurostat
GDP here, or a Eurostat numerator by the BFS GDP.

Swiss quirks, verified against the live API (2026-10-22):
  * nama_10_gdp needs unit=CP_MNAC; CP_MCHF is a well-formed EMPTY cube
    under HTTP 200.
  * No EDP tables for CH (gov_10dd_edpt1 / gov_10dd_ggd have geo size 0)
    and no Maastricht yield (irt_lt_mcby_a): neither is fetched here.
  * Citizenship cuts use FOR_STLS (citizen=FOR is EMPTY); the
    country-of-birth cuts (pop3ctb, imm3ctb) use FOR, which works.
  * The assault code in hlth_cd_aro is X85-Y09_Y871; plain X85-Y09 is
    EMPTY. Suicide is X60-X84_Y870.
  * ilc_li02 has no indic_il dimension (HTTP 400 if sent): statinfo x
    rskpovth, keyed here on MED_EI / B_60.
  * migr_resfirst has 2019 and 2020 MISSING for CH. Holes stay blank.

Every query fails loudly on an empty result: with this API a bad code is
not an error, it is an empty cube under HTTP 200.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache"

BASE = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/"
        "data/{dataset}")
WB = ("https://api.worldbank.org/v2/country/CHE/indicator/{code}"
      "?format=json&per_page=200")

GEO = "CH"
PAUSE = 1.0  # seconds between live requests; Eurostat is generous, be polite

OLD_VINTAGE = ("RATIO DENOMINATOR: Eurostat's Swiss GDP, which for 2023+ is "
               "the PREVIOUS BFS vintage (pre-2026-08-25 revision; 2024 CHF "
               "854.0bn vs BFS 860.9bn). Never mix with BFS-vintage ratios.")

COFOG = {
    "social_protection": "GF10",
    "health": "GF07",
    "general_services": "GF01",   # incl. interest on the debt
    "education": "GF09",
    "economic_affairs": "GF04",
}
COFOG_SUMS = {"defence_order": ("GF02", "GF03"),
              "other": ("GF05", "GF06", "GF08")}


# ---- minimal Eurostat JSON-stat client (cached in cache/) -------------

def strides(size: list[int]) -> list[int]:
    """Row-major strides: JSON-stat varies the LAST dimension fastest."""
    out = [1] * len(size)
    for i in range(len(size) - 2, -1, -1):
        out[i] = out[i + 1] * size[i + 1]
    return out


def decode(payload: dict) -> dict[tuple[str, ...], float]:
    """{(code, ..., time): value} for every populated cell."""
    ids, size = payload["id"], payload["size"]
    cats = []
    for dim in ids:
        index = payload["dimension"][dim]["category"]["index"]
        if isinstance(index, dict):
            cats.append({pos: code for code, pos in index.items()})
        else:
            cats.append(dict(enumerate(index)))
    st = strides(size)
    out = {}
    for flat, value in payload["value"].items():
        n = int(flat)
        key = tuple(cats[i][(n // st[i]) % size[i]] for i in range(len(ids)))
        out[key] = value
    return out


def shape_check(dataset: str, filters: dict, payload: dict) -> None:
    """Refuse to cache a payload that is not a populated Swiss cube.

    The API's failure mode is a well-formed EMPTY cube under HTTP 200 (a
    dimension of size 0, or an empty value map) — that must be a loud
    error, never a cached blank series.
    """
    if "value" not in payload or "id" not in payload:
        raise RuntimeError(f"eurostat {dataset} {filters}: not JSON-stat")
    if 0 in payload["size"]:
        empty = [d for d, n in zip(payload["id"], payload["size"]) if n == 0]
        raise RuntimeError(f"eurostat {dataset} {filters}: EMPTY cube — "
                           f"dimension(s) {empty} have size 0 (bad code?)")
    if not payload["value"]:
        raise RuntimeError(f"eurostat {dataset} {filters}: EMPTY cube — "
                           "no populated cells")
    geo = payload["dimension"].get("geo", {}).get("category", {}).get("index")
    if not geo or list(geo) != [GEO]:
        raise RuntimeError(f"eurostat {dataset}: geo is {geo}, want {GEO}")


def get_json(url: str) -> dict:
    """GET with back-off on 429/403/5xx; 400/404 fail at once (bad query)."""
    last = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "worldreports-fetch/1.0"})
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (400, 404):
                body = e.read()[:300].decode("utf-8", "replace")
                raise RuntimeError(f"{url}: HTTP {e.code} {body}") from e
            wait = 30 * (attempt + 1) if e.code in (429, 403) else 5
            time.sleep(wait)
        except Exception as e:  # noqa: BLE001 — network hiccups
            last = e
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"{url}: {last}")


def fetch(dataset: str, **filters) -> dict:
    """One Eurostat cube, shape-checked, then cached under cache/."""
    CACHE.mkdir(exist_ok=True)
    key = dataset + "_" + "_".join(
        f"{k}-{v}" for k, v in sorted(filters.items()))
    cache_file = CACHE / f"estat_{key}.json"
    if cache_file.exists():
        payload = json.loads(cache_file.read_text())
        shape_check(dataset, filters, payload)
        return payload
    query = urllib.parse.urlencode(
        {"format": "JSON", "lang": "EN", "geo": GEO, **filters})
    payload = get_json(f"{BASE.format(dataset=dataset)}?{query}")
    shape_check(dataset, filters, payload)
    cache_file.write_text(json.dumps(payload))
    time.sleep(PAUSE)
    return payload


def series(dataset: str, **filters) -> dict[str, float]:
    """One series as {period: value}; every non-time dimension pinned.

    A cube that still holds several series is an error (returning one of
    them would be a silent guess), and so is an empty one.
    """
    payload = fetch(dataset, **filters)
    ids = payload["id"]
    free = [d for d, n in zip(ids, payload["size"]) if n > 1 and d != "time"]
    if free:
        raise RuntimeError(f"{dataset} {filters}: {free} left unpinned")
    t = ids.index("time")
    out = {k[t]: v for k, v in decode(payload).items()
           if isinstance(v, (int, float))}
    if not out:
        raise RuntimeError(f"{dataset} {filters}: empty result")
    return out


def annual(dataset: str, **filters) -> dict[int, float]:
    return {int(p): v for p, v in series(dataset, freq="A", **filters).items()}


def worldbank(code: str) -> dict[int, float]:
    """A World Bank WDI series for CHE — the second source for magnitudes."""
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / f"estat_xcheck_wb_{code}.json"
    if cache_file.exists():
        payload = json.loads(cache_file.read_text())
    else:
        payload = get_json(WB.format(code=code))
        if (not isinstance(payload, list) or len(payload) < 2
                or not payload[1]):
            raise RuntimeError(f"World Bank {code}: empty or malformed")
        cache_file.write_text(json.dumps(payload))
        time.sleep(PAUSE)
    return {int(r["date"]): r["value"] for r in payload[1]
            if r.get("value") is not None}


# ---- spot checks -------------------------------------------------------

FAILED: list[str] = []


def check(name: str, got: float | None, want: float, tol: float = 0.051):
    """Pin today's vintage against the value verified in discovery.

    Eurostat revises; a mismatch means RE-VERIFY (and, for GDP, re-read the
    vintage labels in the CSV comments) — never silence it.
    """
    ok = got is not None and abs(got - want) <= tol
    print(f"  check {name}: got {got} want {want} -> "
          f"{'ok' if ok else 'MISMATCH'}")
    if not ok:
        FAILED.append(f"{name}: got {got}, want {want}")


# ---- sidecar writing ---------------------------------------------------

def write(rel: str, comment: str, columns: dict[str, dict], dec: int,
          key: str = "year", periods: list | None = None) -> None:
    """A wide CSV with a `#` comment header; blanks where Eurostat has none.

    Rows run over the whole span the source covers (first to last
    populated period across the columns); interior holes stay blank.
    """
    if periods is None:
        have = sorted(set().union(*(set(s) for s in columns.values())))
        periods = list(range(have[0], have[-1] + 1))
    lines = ["# " + ln for ln in wrap(comment)]
    lines.append(key + "," + ",".join(columns))
    for p in periods:
        cells = []
        for s in columns.values():
            v = s.get(p)
            cells.append("" if v is None else f"{v:.{dec}f}")
        lines.append(f"{p}," + ",".join(cells))
    path = DATA / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
    print(f"  -> data/{rel}: {len(periods)} rows {periods[0]}–{periods[-1]}")


def wrap(text: str, width: int = 76) -> list[str]:
    out, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            out.append(line)
            line = word
        else:
            line = f"{line} {word}" if line else word
    return out + [line] if line else out


# ---- the chapters ------------------------------------------------------

def macro() -> None:
    nominal = annual("nama_10_gdp", na_item="B1GQ", unit="CP_MNAC")
    growth = annual("nama_10_gdp", na_item="B1GQ", unit="CLV_PCH_PRE")
    for y, want in ((2006, 562159.6), (2020, 709854.6), (2023, 834189.8),
                    (2024, 853957.0), (2025, 867544.7)):
        check(f"GDP {y} CHF mn (old vintage from 2023)", nominal.get(y),
              want, tol=0.5)
    # Second source: World Bank GDP in current LCU, which carries the SAME
    # previous BFS vintage — a match also confirms Eurostat has not yet
    # taken the 2026-08 revision (if it has, the vintage notes are stale).
    wb = worldbank("NY.GDP.MKTP.CN")
    rel = wb[2024] / 1e6 / nominal[2024] - 1
    print(f"  xcheck GDP 2024 Eurostat {nominal[2024]:.1f} vs World Bank "
          f"{wb[2024] / 1e6:.1f} CHF mn ({rel:+.2%})")
    if abs(rel) > 0.005:
        FAILED.append(f"GDP 2024 Eurostat vs World Bank off by {rel:+.2%}")
    write("macro/gdp_from_estat.csv",
          "Eurostat nama_10_gdp, Switzerland (BFS transmission). gdp_chf_mn "
          "= GDP at current prices, CHF MILLIONS (unit CP_MNAC); "
          "real_growth_pct = volume change on previous year, % "
          "(CLV_PCH_PRE). VINTAGE: equal to BFS through 2022; for 2023+ "
          "this is the PREVIOUS BFS vintage, before the 2026-08-25 revision "
          "(2024 854.0bn here vs 860.9bn at BFS). The harmonised twin of "
          "gdp_from_bfs.csv — never spliced with it.",
          {"gdp_chf_mn": nominal, "real_growth_pct": growth}, dec=1)

    q = series("namq_10_gdp", freq="Q", na_item="B1GQ", unit="CLV_PCH_PRE",
               s_adj="SCA")
    for p, want in (("2008-Q4", -2.2), ("2009-Q1", -1.7), ("2015-Q1", -0.3),
                    ("2020-Q2", -6.3), ("2026-Q2", 1.9)):
        check(f"GDP q/q {p}", q.get(p), want)
    quarters = sorted(q, key=lambda s: (int(s[:4]), int(s[-1])))
    first, last = quarters[0], quarters[-1]
    span = [f"{y}-Q{n}" for y in range(int(first[:4]), int(last[:4]) + 1)
            for n in range(1, 5)
            if first <= f"{y}-Q{n}" <= last]
    write("macro/gdp_quarterly_from_estat.csv",
          "Eurostat namq_10_gdp, Switzerland: real GDP, % change on the "
          "previous quarter, seasonally and calendar adjusted (CLV_PCH_PRE, "
          "SCA). NOT adjusted for major sporting events, so it differs from "
          "SECO gdp_cssa by tenths (2015-Q1 -0.3 here vs -0.0). Quarterly "
          "national accounts vintage as published by Eurostat.",
          {"qoq_real_pct": q}, dec=1, key="quarter", periods=span)

    hicp = annual("prc_hicp_aind", coicop="CP00", unit="RCH_A_AVG")
    for y, want in ((2009, -0.7), (2015, -0.8), (2023, 2.3), (2025, 0.1)):
        check(f"HICP {y}", hicp.get(y), want)
    write("macro/hicp_from_estat.csv",
          "Eurostat prc_hicp_aind, Switzerland: HICP all items (CP00), "
          "annual average rate of change, % (RCH_A_AVG). Computed by BFS to "
          "the harmonised method; NOT the LIK (national CPI) — they differ "
          "by tenths (2015: -0.8 vs -1.1). Beside the LIK, never spliced.",
          {"hicp_pct": hicp}, dec=1)

    unemp = annual("lfsa_urgan", citizen="TOTAL", age="Y15-74", sex="T",
                   unit="PC")
    for y, want in ((2006, 4.0), (2009, 4.1), (2025, 4.9)):
        check(f"LFS unemployment {y}", unemp.get(y), want)
    write("macro/unemployment_from_estat.csv",
          "Eurostat lfsa_urgan, Switzerland: ILO unemployment rate, ages "
          "15-74, all citizenships, % of the labour force (SAKE/LFS survey). "
          "lfsa_urgan is used because une_rt_a starts only in 2010 for CH. "
          "SURVEY measure: never one line with SECO registered "
          "unemployment.",
          {"ilo_rate_pct": unemp}, dec=1)


def fiscal() -> None:
    gg = {item: annual("gov_10a_main", sector="S13", unit="PC_GDP",
                       na_item=item)
          for item in ("B9", "TR", "TE", "D41PAY")}
    check("GG balance 2020 %GDP", gg["B9"].get(2020), -2.6)
    check("GG balance 2024 %GDP", gg["B9"].get(2024), 0.3)
    check("GG revenue 2024 %GDP", gg["TR"].get(2024), 33.1)
    check("GG expenditure 2024 %GDP", gg["TE"].get(2024), 32.8)
    write("fiscal/general_government_from_estat.csv",
          "Eurostat gov_10a_main, Switzerland, general government (S13), "
          "ESA 2010, % of GDP: balance = net lending(+)/borrowing(-) B9; "
          "revenue = TR; expenditure = TE; interest = D41 payable. Calendar "
          "years (the Swiss fiscal year is the calendar year). Not EDP "
          "data: Eurostat's EDP tables do not cover CH. " + OLD_VINTAGE +
          " So these differ from EFV's ratios by tenths.",
          {"balance_pct_gdp": gg["B9"], "revenue_pct_gdp": gg["TR"],
           "expenditure_pct_gdp": gg["TE"],
           "interest_pct_gdp": gg["D41PAY"]}, dec=1)

    taxes = annual("gov_10a_taxag", sector="S13_S212", unit="PC_GDP",
                   na_item="D2_D5_D91_D61_M_D995")
    check("tax burden 2024 %GDP", taxes.get(2024), 27.8)
    write("fiscal/tax_burden_from_estat.csv",
          "Eurostat gov_10a_taxag, Switzerland: total taxes and social "
          "contributions after deduction of amounts assessed but unlikely "
          "to be collected (D2_D5_D91_D61_M_D995), general government plus "
          "EU institutions (S13_S212), % of GDP. " + OLD_VINTAGE +
          " Beside EFV's Fiskalquote (26.7% in 2024) and the extended "
          "ratio (37.3%), never spliced: the gap to the extended ratio is "
          "compulsory health insurance and BVG pension contributions, which "
          "are not taxes in the national accounts.",
          {"tax_burden_pct_gdp": taxes}, dec=1)

    cofog = {name: annual("gov_10a_exp", sector="S13", unit="PC_GDP",
                          na_item="TE", cofog99=code)
             for name, code in COFOG.items()}
    parts = {c: annual("gov_10a_exp", sector="S13", unit="PC_GDP",
                       na_item="TE", cofog99=c)
             for codes in COFOG_SUMS.values() for c in codes}
    # A summed line exists only in years where EVERY part is published: a
    # missing division is a hole, never a zero folded into the sum.
    for name, codes in COFOG_SUMS.items():
        common = set.intersection(*(set(parts[c]) for c in codes))
        cofog[name] = {y: sum(parts[c][y] for c in codes) for y in common}
    cofog["total"] = annual("gov_10a_exp", sector="S13", unit="PC_GDP",
                            na_item="TE", cofog99="TOTAL")
    check("COFOG total 2020 %GDP", cofog["total"].get(2020), 37.4)
    check("COFOG total 2024 %GDP", cofog["total"].get(2024), 32.5)
    write("fiscal/spending_by_function_from_estat.csv",
          "Eurostat gov_10a_exp (COFOG), Switzerland, general government "
          "(S13), total expenditure by function, % of GDP. defence_order = "
          "GF02 defence + GF03 public order; other = GF05 environment + GF06 "
          "housing + GF08 recreation/culture/religion, summed only in years "
          "where every part is published. general_services (GF01) includes "
          "interest on the debt. The 2020 spike is the COVID short-time "
          "work and loan programmes. " + OLD_VINTAGE,
          cofog, dec=2)


def social() -> None:
    gini = annual("ilc_di12", age="TOTAL", statinfo="GINI_HND")
    check("Gini 2015", gini.get(2015), 29.6)
    check("Gini 2024", gini.get(2024), 31.0)
    write("social/gini_from_estat.csv",
          "Eurostat ilc_di12, Switzerland: Gini coefficient of equivalised "
          "disposable income, 0-100 scale, whole population (EU-SILC, "
          "collected by BFS). SILC income year is the year before the "
          "survey year shown. CH series starts 2014 in this table.",
          {"gini": gini}, dec=1)

    arop = annual("ilc_li02", sex="T", age="TOTAL", unit="PC",
                  statinfo="MED_EI", rskpovth="B_60")
    check("at-risk-of-poverty 2024 %", arop.get(2024), 16.2)
    if not 10 <= arop[2024] <= 20:
        FAILED.append("at-risk-of-poverty rate outside a 10-20% sanity band")
    write("social/poverty_from_estat.csv",
          "Eurostat ilc_li02, Switzerland: at-risk-of-poverty rate, % of "
          "persons below 60% of national median equivalised disposable "
          "income after social transfers (statinfo MED_EI, rskpovth B_60), "
          "EU-SILC. A relative-income line, not BFS's absolute poverty "
          "line (Armutsquote) — two measures, never one line.",
          {"arop60_pct": arop}, dec=1)


def demography() -> None:
    pop = annual("demo_gind", indic_de="JAN")
    check("population 1-Jan-2006", pop.get(2006), 7459128, tol=0.5)
    check("population 1-Jan-2025", pop.get(2025), 9051029, tol=0.5)
    check("population 1-Jan-2026", pop.get(2026), 9124288, tol=0.5)
    # Second source: World Bank mid-year population against the mean of
    # Eurostat's two bracketing 1-January stocks.
    wb = worldbank("SP.POP.TOTL")
    mid = (pop[2025] + pop[2026]) / 2
    rel = wb[2025] / mid - 1
    print(f"  xcheck population mid-2025 Eurostat {mid:,.0f} vs World Bank "
          f"{wb[2025]:,.0f} ({rel:+.2%})")
    if abs(rel) > 0.005:
        FAILED.append(f"population 2025 vs World Bank off by {rel:+.2%}")
    write("demography/population_from_estat.csv",
          "Eurostat demo_gind, Switzerland: population on 1 JANUARY, "
          "persons (permanent resident population, BFS transmission). "
          "1-Jan-2026 is the provisional transmission and sits 2,837 below "
          "the BFS definitive 31-Dec-2025 stock. Cross-check only.",
          {"population_jan1": pop}, dec=0)


def security() -> None:
    hom = annual("crim_off_cat", iccs="ICCS0101", unit="NR")
    for y, want in ((2008, 54), (2015, 57), (2024, 45)):
        check(f"police-recorded homicides {y}", hom.get(y), want, tol=0)
    write("security/homicide_police_from_estat.csv",
          "Eurostat crim_off_cat, Switzerland: intentional homicide "
          "(ICCS0101), police-recorded offences, number. Equals the PKS "
          "completed ('vollendet') count where both exist; attempts are "
          "NOT included. Carries 2008, which the PKS API does not.",
          {"homicides": hom}, dec=0)


def mortality() -> None:
    codes = {"all_causes": "TOTAL", "assault": "X85-Y09_Y871",
             "suicide": "X60-X84_Y870", "covid19": "U071"}
    cols = {name: annual("hlth_cd_aro", sex="T", age="TOTAL",
                         resid="TOT_IN", unit="NR", icd10=code)
            for name, code in codes.items()}
    check("assault deaths 2022", cols["assault"].get(2022), 35, tol=0)
    check("suicides 2024", cols["suicide"].get(2024), 1043, tol=0)
    check("COVID-19 deaths 2022", cols["covid19"].get(2022), 4136, tol=0)
    write("mortality/deaths_by_cause_from_estat.csv",
          "Eurostat hlth_cd_aro, Switzerland: deaths by underlying cause, "
          "number, all deaths reported in the country (resid TOT_IN), both "
          "sexes, all ages. assault = X85-Y09 + Y87.1; suicide = X60-X84 + "
          "Y87.0; covid19 = U07.1. The series starts 2011, after BFS moved "
          "assisted suicide out of suicide (from 2009 it is coded to the "
          "underlying disease). Assault deaths (death certificates) are not "
          "police-recorded homicides (2022: 35 vs 42) — never spliced.",
          cols, dec=0)


def credit() -> None:
    ratio = annual("nasa_10_f_bs", sector="S14_S15", na_item="F4",
                   finpos="LIAB", co_nco="NCO", unit="PC_GDP")
    level = annual("nasa_10_f_bs", sector="S14_S15", na_item="F4",
                   finpos="LIAB", co_nco="NCO", unit="MIO_NAC")
    for y, want in ((2006, 105.7), (2015, 120.2), (2020, 132.4),
                    (2025, 123.0)):
        check(f"household loans {y} %GDP", ratio.get(y), want)
    write("credit/household_debt_from_estat.csv",
          "Eurostat nasa_10_f_bs, Switzerland: loans (F4) owed by "
          "households and NPISH (S14_S15), non-consolidated, end-year "
          "stock. loans_pct_gdp is Eurostat's ratio; loans_chf_mn is the "
          "level in CHF MILLIONS (MIO_NAC). " + OLD_VINTAGE + " (SNB 2025 "
          "loans over BFS GDP gives about 121.0%, not 123.0.) The long "
          "series beside the SNB financial accounts (levels equal; the SNB "
          "files carry no ratio), never spliced.",
          {"loans_pct_gdp": ratio, "loans_chf_mn": level}, dec=1)


def migration() -> None:
    cit = {"total": "TOTAL", "national": "NAT", "foreign": "FOR_STLS",
           "eu27": "EU27_2020_FOR", "non_eu27": "NEU27_2020_FOR"}
    birth = {"total": "TOTAL", "native": "NAT", "foreign_born": "FOR"}

    def cut(dataset: str, dim: str, codes: dict, prefix: str,
            **extra) -> dict[str, dict[int, float]]:
        return {f"{prefix}_{col}": annual(dataset, age="TOTAL", sex="T",
                                          unit="NR", **{dim: code}, **extra)
                for col, code in codes.items()}

    flows = {**cut("migr_imm1ctz", "citizen", cit, "imm", agedef="COMPLET"),
             **cut("migr_imm3ctb", "c_birth", birth, "imm_bybirth",
                   agedef="COMPLET"),
             **cut("migr_emi1ctz", "citizen", cit, "emi", agedef="COMPLET")}
    check("immigration 2023", flows["imm_total"].get(2023), 263081, tol=0)
    # DEFINITIONAL SEAMS (consolidation, 2026-10-22): against the BFS
    # balance, imm1ctz equals BFS immigration INCLUDING changes of
    # population type in 2000-2010 and 2023-2024, but EXCLUDES them in
    # 2011-2022 (the gap is exactly BFS's type-change component every
    # year). These spot values pin both regimes so a re-transmission fails.
    check("immigration 2010 (incl. type change)", flows["imm_total"].get(2010),
          161778, tol=0)
    check("immigration 2015 (excl. type change)", flows["imm_total"].get(2015),
          153627, tol=0)
    check("immigration 2022 (excl. type change)", flows["imm_total"].get(2022),
          167079, tol=0)
    check("emigration 2024", flows["emi_total"].get(2024), 129786, tol=0)
    # The two immigration cuts are the same BFS flow under two keys.
    for y in set(flows["imm_total"]) & set(flows["imm_bybirth_total"]):
        if flows["imm_total"][y] != flows["imm_bybirth_total"][y]:
            FAILED.append(f"imm1ctz vs imm3ctb totals differ in {y}")
    write("migration/flows_from_estat.csv",
          "Eurostat migr_imm1ctz / migr_imm3ctb / migr_emi1ctz, "
          "Switzerland, persons, age in completed years. THE DEFINITION "
          "CHANGES ACROSS YEARS: in 2000-2010 and 2023-2024 immigration "
          "INCLUDES changes of population type (a person 12 months in the "
          "non-permanent population — asylum seekers, S status, L permits — "
          "counted as an immigrant on moving into the permanent one) and "
          "equals BFS; in 2011-2022 it EXCLUDES them and sits below BFS by "
          "exactly BFS's type-change component (2015: 153,627 vs 188,515). "
          "Two seams, 2010/11 and 2022/23: never one line across them. The "
          "2023 peak is largely Ukrainians with S status. Emigration equals "
          "BFS in every year. foreign = "
          "FOR_STLS (foreign + stateless; citizen=FOR is an empty cube for "
          "CH). imm_bybirth_* is by country of birth, 2011+ only.",
          flows, dec=0)

    stock = {**cut("migr_pop1ctz", "citizen", cit, "pop"),
             **cut("migr_pop3ctb", "c_birth", birth, "pop_bybirth")}
    check("foreign citizens 1-Jan-2006", stock["pop_foreign"].get(2006),
          1541825, tol=0)
    check("foreign citizens 1-Jan-2025", stock["pop_foreign"].get(2025),
          2478134, tol=0)
    check("foreign-born 1-Jan-2025", stock["pop_bybirth_foreign_born"].get(
        2025), 2870124, tol=0)
    write("migration/stock_from_estat.csv",
          "Eurostat migr_pop1ctz (citizenship) and migr_pop3ctb (country of "
          "birth), Switzerland, persons on 1 January. pop_foreign = "
          "FOR_STLS (citizen=FOR is empty for CH); pop_bybirth_foreign_born "
          "= c_birth FOR, 2011+. The gap between the two is largely the "
          "naturalised foreign-born. Permanent resident population (BFS "
          "STATPOP), not SEM's ZEMIS register.",
          stock, dec=0)

    asy_all = annual("migr_asyappctza", citizen="TOTAL", applicant="TOTAL",
                     sex="T", age="TOTAL", unit="PER")
    asy_first = annual("migr_asyappctza", citizen="TOTAL", applicant="FRST",
                       sex="T", age="TOTAL", unit="PER")
    dec_all = annual("migr_asydcfsta", citizen="TOTAL", sex="T",
                     age="TOTAL", unit="PER", decision="TOTAL")
    dec_pos = annual("migr_asydcfsta", citizen="TOTAL", sex="T",
                     age="TOTAL", unit="PER", decision="POS")
    for y, want in ((2015, 38120), (2023, 26895), (2025, 23415)):
        check(f"first-time asylum applicants {y}", asy_first.get(y), want,
              tol=0)
    check("first-instance decisions 2024", dec_all.get(2024), 24765, tol=0)
    write("migration/asylum_from_estat.csv",
          "Eurostat migr_asyappctza and migr_asydcfsta, Switzerland, "
          "persons (SEM reports to Eurostat). applicants = all asylum "
          "applicants; first_time = first-time applicants; decisions = "
          "first-instance decisions, total and positive. Ukrainian S status "
          "(temporary protection) is NOT asylum and is not in these tables.",
          {"applicants": asy_all, "first_time": asy_first,
           "decisions": dec_all, "decisions_positive": dec_pos}, dec=0)

    first = annual("migr_resfirst", citizen="TOTAL", reason="TOTAL",
                   duration="TOTAL", unit="PER")
    valid = annual("migr_resvalid", citizen="TOTAL", reason="TOTAL",
                   duration="TOTAL", unit="PER")
    check("first permits 2015", first.get(2015), 41105, tol=0)
    check("first permits 2025", first.get(2025), 46272, tol=0)
    check("valid permits 2025", valid.get(2025), 813792, tol=0)
    if 2019 in first or 2020 in first:
        FAILED.append("migr_resfirst now carries 2019/2020 for CH — the "
                      "documented hole changed; re-verify the comment")
    write("migration/permits_from_estat.csv",
          "Eurostat migr_resfirst (first permits issued in the year) and "
          "migr_resvalid (permits valid on 31 December), Switzerland, "
          "THIRD-COUNTRY nationals only (EU/EFTA citizens are outside these "
          "tables), persons. first_permits 2019 and 2020 are MISSING in "
          "the source and stay blank.",
          {"first_permits": first, "valid_permits": valid}, dec=0)

    acq = annual("migr_acq", citizen="TOTAL", age="TOTAL", sex="T",
                 agedef="COMPLET", unit="NR")
    check("naturalisations 2006", acq.get(2006), 46711, tol=0)
    check("naturalisations 2024", acq.get(2024), 39912, tol=0)
    write("migration/citizenship_from_estat.csv",
          "Eurostat migr_acq, Switzerland: acquisitions of Swiss "
          "citizenship, persons. Equals the naturalisations in the BFS "
          "population balance; BFS carries the latest year first.",
          {"acquisitions": acq}, dec=0)

    irr = annual("migr_eipre", citizen="TOTAL", age="TOTAL", sex="T",
                 unit="PER", reason="TOTAL", apprehen="TOTAL")
    check("irregular presence 2015", irr.get(2015), 15555, tol=0)
    check("irregular presence 2025", irr.get(2025), 15300, tol=0)
    write("migration/irregular_from_estat.csv",
          "Eurostat migr_eipre, Switzerland (Schengen member): third-country "
          "nationals found to be illegally present, all reasons, all places "
          "of apprehension. Counts EVENTS of apprehension, not persons.",
          {"found_illegally_present": irr}, dec=0)


def main() -> None:
    print("Fetching Eurostat series for Switzerland (geo=CH)...")
    for chapter in (macro, fiscal, social, demography, security, mortality,
                    credit, migration):
        chapter()
    if FAILED:
        raise RuntimeError("spot checks failed:\n  " + "\n  ".join(FAILED))
    print("Done. Diff the *_from_estat.csv sidecars before adopting.")


if __name__ == "__main__":
    main()
