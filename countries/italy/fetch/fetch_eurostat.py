#!/usr/bin/env python3
"""Refresh the Eurostat-backed series for Italy into sidecar CSVs.

Usage:  python3 -I countries/italy/fetch/fetch_eurostat.py

Everything here is a series Italy reports to Eurostat under a statistical
obligation — the ESA 2010 national accounts, the EDP (Maastricht) fiscal
notification, COFOG expenditure, the LFS unemployment rate, the HICP — or
the harmonised migration suite that SOURCING_A_COUNTRY.md §4a makes the
system of record for an EU member. Eurostat is the authoritative
publication channel for all of it. Where ISTAT publishes its own national
series of the same thing (the NIC, the RFL unemployment rate, the
anagraphic migration flows), ISTAT is the primary and this is the
cross-check; the pairs are kept as separate files, never spliced.

Output goes to `*_from_estat.csv` sidecars, never over a curated file.

Italy-specific notes, verified against the live API (2026-10-22):
  * gov_10a_taxag only answers with na_item=D2_D5_D91_D61_M_D995 and
    sector=S13_S212; na_item=TR returns a well-formed EMPTY cube.
  * ilc_di12's dimension is statinfo=GINI_HND — asking for indic_il is
    HTTP 400 "Dimension INDIC_IL is not defined".
  * une_rt_a starts 2009 for Italy: 2006-2008 are real absences in the
    source, carried as blanks (the ISTAT old-regulation RFL is the only
    2006-2008 coverage; see SOURCES.yaml meta.pending).
  * migr_pop1ctz's foreign-citizen aggregate is citizen=FOR_STLS, not
    FOR — citizen=FOR returns well-formed and EMPTY under HTTP 200 (the
    endpoint's silent-truncation trap, same family as Spain's unit=NR).
    The country-of-birth twin migr_pop3ctb DOES use FOR. Both stock
    files therefore carry an explicit `foreign` column on the code that
    actually exists, and the fetcher fails on an empty result.
  * migr_asyappctza and migr_resfirst need unit=PER; unit=NR is the
    same silent empty cube as in Spain.
  * NO EM/EMCR-style splice: Italy transmits one immigration flow under
    both definitions, so the migr_imm1ctz and migr_imm3ctb TOTALS are
    identical 2008-2024. The fetcher asserts that still holds — if a
    future revision breaks it, the plates' story changes and this must
    fail loudly, not pass silently.
  * The pre-2021 `_UNT2020` old-regulation labour twins are an ISTAT
    matter (flows 150_1175/151_1178 vs 150_883/151_884), handled by
    fetch_istat.py — Eurostat's harmonised LFS has no such twin.
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache"

BASE = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/"
        "data/{dataset}")

GEO = "IT"
Y0, Y1 = 2006, 2026

COFOG = {
    "social_protection": "GF10",
    "health": "GF07",
    "general_services": "GF01",   # incl. interest on the debt
    "education": "GF09",
    "economic_affairs": "GF04",
    "defence_order": None,        # GF02 + GF03, summed below
    "other": None,                # GF05 + GF06 + GF08, summed below
}

# The citizenship and country-of-birth cuts share these aggregate codes;
# the pair (same quantity, two definitions) is the point of the chapter.
CUTS = {"total": "TOTAL", "national": "NAT",
        "eu27": "EU27_2020_FOR", "non_eu27": "NEU27_2020_FOR"}

# The foreign aggregate differs BY DATASET in Italy's transmission:
# FOR_STLS (foreign + stateless) on the citizenship cut, FOR on the
# country-of-birth cut. Naming the wrong one is a silent empty cube.
STOCK_FOREIGN = {"migr_pop1ctz": "FOR_STLS", "migr_pop3ctb": "FOR"}


# ---- minimal Eurostat JSON-stat client (cached in cache/) -------------

def strides(size: list[int]) -> list[int]:
    """Row-major strides for a cube of these dimension sizes.

    JSON-stat numbers its cells with the LAST dimension varying fastest, so
    the stride of dimension i is the product of every size after it.
    """
    out = [1] * len(size)
    for i in range(len(size) - 2, -1, -1):
        out[i] = out[i + 1] * size[i + 1]
    return out


def decode(payload: dict) -> dict[tuple[str, ...], float]:
    """{(code, code, ..., time): value} for every populated cell.

    The key is the dimension codes in the cube's own dimension order, so
    the caller reads it with `payload["id"].index("time")` rather than
    guessing.
    """
    ids, size = payload["id"], payload["size"]
    cats = []
    for dim in ids:
        index = payload["dimension"][dim]["category"]["index"]
        if isinstance(index, dict):
            cats.append({pos: code for code, pos in index.items()})
        else:  # a single-category dimension may come back as a bare list
            cats.append(dict(enumerate(index)))
    st = strides(size)
    out = {}
    for flat, value in payload["value"].items():
        n = int(flat)
        key = tuple(cats[i][(n // st[i]) % size[i]] for i in range(len(ids)))
        out[key] = value
    return out


def fetch(dataset: str, cache_key: str | None = None, **filters) -> dict:
    """One Eurostat cube, cached under cache/ so re-runs are free."""
    CACHE.mkdir(exist_ok=True)
    key = cache_key or dataset + "_" + "_".join(
        f"{k}-{v}" for k, v in sorted(filters.items()))
    cache_file = CACHE / f"estat_{key}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    query = urllib.parse.urlencode({"format": "JSON", **filters}, doseq=True)
    url = f"{BASE.format(dataset=dataset)}?{query}"
    last = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                payload = json.loads(r.read())
            if "value" not in payload:
                raise ValueError("no value map in response")
            cache_file.write_text(json.dumps(payload))
            return payload
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"eurostat {dataset} {filters}: {last}")


def annual(dataset: str, cache_key: str | None = None,
           **filters) -> dict[int, float]:
    """A single annual series as {year: value}.

    Every dimension except `time` must be pinned by a filter, otherwise the
    cube carries more than one series and silently returning one of them is
    exactly the kind of error this repo exists to avoid.
    """
    payload = fetch(dataset, cache_key, **filters)
    ids = payload["id"]
    free = [d for d, n in zip(ids, payload["size"]) if n > 1 and d != "time"]
    if free:
        raise ValueError(
            f"{dataset}: {free} left unpinned — the cube holds several series")
    t = ids.index("time")
    out = {}
    for key, value in decode(payload).items():
        period = key[t]
        if period.isdigit():
            out[int(period)] = value
    return out


# ---- sidecar writing ---------------------------------------------------

def rows(years, columns: dict[str, dict[int, float]],
         dec: int | dict[str, int] = 2) -> str:
    """A wide CSV: one row per year, blanks where the source has no value.

    `dec` is one precision for every column, or a per-column mapping (a
    count is written as a whole number, a rate with its decimals).
    """
    head = "year," + ",".join(columns)
    lines = [head]
    for y in years:
        cells = []
        for name, series in columns.items():
            v = series.get(y)
            d = dec[name] if isinstance(dec, dict) else dec
            cells.append("" if v is None else f"{v:.{d}f}")
        lines.append(f"{y}," + ",".join(cells))
    return "\n".join(lines) + "\n"


def write(rel: str, text: str) -> None:
    path = DATA / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    print(f"  -> data/{rel}")


def migration(dataset: str, dim: str, name: str,
              agedef: bool = False) -> dict[str, dict[int, float]]:
    """The four CUTS of one migration dataset as {column: {year: value}}.

    An empty result means the filters named nothing — with this API that
    is how a bad unit or a removed code presents, so it fails loudly.
    Flow datasets (and migr_acq) carry an `agedef` dimension the stock
    ones do not; it is pinned to REACH where it exists. Stock datasets
    add a `foreign` column on the aggregate code that actually exists
    for that dataset (STOCK_FOREIGN) — the wrong code is a silent empty
    cube, so it is named explicitly rather than guessed.
    """
    cuts = dict(CUTS)
    if dataset in STOCK_FOREIGN:
        cuts = {"total": "TOTAL", "national": "NAT",
                "foreign": STOCK_FOREIGN[dataset],
                "eu27": "EU27_2020_FOR", "non_eu27": "NEU27_2020_FOR"}
    out = {}
    for col, code in cuts.items():
        extra = {"agedef": "REACH"} if agedef else {}
        series = annual(dataset, geo=GEO, unit="NR", sex="T", age="TOTAL",
                        freq="A", cache_key=f"{dataset}_{dim}_{code}",
                        **{dim: code}, **extra)
        if not series:
            raise RuntimeError(f"{dataset} {dim}={code}: empty result")
        out[f"{name}_{col}"] = {y: v for y, v in series.items()
                                if isinstance(v, (int, float))}
    return out


# ---- must-verify spot checks (values verified live 2026-10-22) ---------

CHECKS: list[tuple[str, float, float, float]] = []


def check(name: str, got: float | None, want: float, tol: float = 0.051):
    """Record one spot check; the run fails at the end if any drifted.

    These pin today's vintage against the figures verified in discovery.
    Eurostat revises, so a failure here means RE-VERIFY the series and
    update the expectation — never silence it.
    """
    ok = got is not None and abs(got - want) <= tol
    print(f"  check {name}: got {got} want {want} -> {'ok' if ok else 'MISMATCH'}")
    if not ok:
        CHECKS.append((name, got, want, tol))


def main() -> None:
    years = list(range(Y0, Y1 + 1))
    print("Fetching Eurostat series for Italy...")

    # ---- national accounts -------------------------------------------
    nominal = annual("nama_10_gdp", geo=GEO, na_item="B1GQ",
                     unit="CP_MEUR", freq="A")
    growth = annual("nama_10_gdp", geo=GEO, na_item="B1GQ",
                    unit="CLV_PCH_PRE", freq="A")
    gfcf = annual("nama_10_gdp", geo=GEO, na_item="P51G",
                  unit="CP_MEUR", freq="A")
    # Eurostat publishes GDP in millions; the plates read billions of euro.
    nominal_bn = {y: v / 1000 for y, v in nominal.items()}
    write("macro/gdp_from_estat.csv",
          rows(years, {"nominal_eurbn": nominal_bn, "real_growth": growth},
               dec=2))

    # Quarterly growth (namq_10_gdp, q/q SA) dates the recession bands in
    # country.yaml; there is no manifest sidecar for it, so it is pulled
    # here only to re-verify the band dating against today's vintage.
    qg = fetch("namq_10_gdp", "namq_10_gdp_it", geo=GEO, na_item="B1GQ",
               unit="CLV_PCH_PRE", s_adj="SCA", freq="Q")
    t = qg["id"].index("time")
    qgrowth = {key[t]: v for key, v in decode(qg).items()}
    bands = {"2008Q2-2009Q2": [f"{y}-Q{q}" for y in (2008, 2009)
                               for q in range(1, 5)
                               if (y, q) >= (2008, 2) and (y, q) <= (2009, 2)],
             "2011Q2-2013Q1": [f"{y}-Q{q}" for y in (2011, 2012, 2013)
                               for q in range(1, 5)
                               if (y, q) >= (2011, 2) and (y, q) <= (2013, 1)],
             "2020Q1-2020Q2": ["2020-Q1", "2020-Q2"]}
    for label, quarters in bands.items():
        vals = [qgrowth.get(q) for q in quarters]
        if any(v is None or v >= 0 for v in vals):
            raise RuntimeError(
                f"namq_10_gdp: band {label} no longer all-negative "
                f"({vals}) — re-date the recession bands in country.yaml")
    print("  check recession bands (namq_10_gdp q/q SA): all-negative ok")

    # ---- EDP / Maastricht: the authoritative fiscal aggregates --------
    deficit = annual("gov_10dd_edpt1", geo=GEO, na_item="B9",
                     unit="PC_GDP", sector="S13", freq="A")
    debt = annual("gov_10dd_edpt1", geo=GEO, na_item="GD",
                  unit="PC_GDP", sector="S13", freq="A")
    interest = annual("gov_10a_main", geo=GEO, na_item="D41PAY",
                      unit="PC_GDP", sector="S13", freq="A")
    revenue = annual("gov_10a_main", geo=GEO, na_item="TR",
                     unit="PC_GDP", sector="S13", freq="A")
    expenditure = annual("gov_10a_main", geo=GEO, na_item="TE",
                         unit="PC_GDP", sector="S13", freq="A")
    gov_gfcf = annual("gov_10a_main", geo=GEO, na_item="P51G",
                      unit="PC_GDP", sector="S13", freq="A")
    # The primary balance is the headline deficit with interest added back:
    # it is what the budget would be if the debt were free, and it is the
    # number that says whether today's policy is adding to the stock.
    # Italy has run primary surpluses almost every year of the window —
    # that is the fiscal plate's story.
    primary = {y: deficit[y] + interest[y] for y in deficit
               if y in interest}
    check("EDP debt 2024 %GDP", debt.get(2024), 134.3)
    check("EDP debt 2025 %GDP", debt.get(2025), 136.7)
    check("EDP deficit 2024 %GDP", deficit.get(2024), -3.4)

    # The debt stock in euro: quarterly EDP debt, read at Q4. A stock read
    # at a moment may show the running year as its latest observed quarter;
    # the plate labels it a latest point, not the year's result.
    qd = fetch("gov_10q_ggdebt", "gov_10q_ggdebt_it",
               geo=GEO, na_item="GD", unit="MIO_EUR", sector="S13", freq="Q")
    t = qd["id"].index("time")
    debt_eur_q4 = {}
    for key, value in decode(qd).items():
        year, _, qtr = key[t].partition("-Q")
        if qtr == "4":
            debt_eur_q4[int(year)] = value / 1000  # MIO_EUR -> bn
    check("EDP debt stock 2025Q4 €bn", debt_eur_q4.get(2025), 3097.1, tol=1.0)

    write("fiscal/debt_from_estat.csv",
          rows(years, {"gross_pct_gdp": debt,
                       "gross_eurbn_q4": debt_eur_q4}, dec=1))
    write("fiscal/deficit_from_estat.csv",
          rows(years, {"deficit": deficit, "primary": primary,
                       "interest": interest}, dec=2))
    write("fiscal/revenue_from_estat.csv",
          rows(years, {"revenue": revenue, "expenditure": expenditure},
               dec=1))

    # ---- taxes: Eurostat's harmonised total ---------------------------
    # na_item=TR returns EMPTY here; the working key is the Spain one.
    taxes = annual("gov_10a_taxag", geo=GEO,
                   na_item="D2_D5_D91_D61_M_D995",
                   unit="PC_GDP", sector="S13_S212", freq="A")
    if not taxes:
        raise RuntimeError("gov_10a_taxag: empty result")
    check("tax take 2024 %GDP", taxes.get(2024), 42.3)
    write("fiscal/tax_burden_from_estat.csv",
          rows(years, {"estat": taxes}, dec=1))

    # ---- COFOG: where the money actually goes ------------------------
    cofog: dict[str, dict[int, float]] = {}
    for name, code in COFOG.items():
        if code:
            cofog[name] = annual("gov_10a_exp", geo=GEO, na_item="TE",
                                 unit="PC_GDP", sector="S13",
                                 cofog99=code, freq="A")
    parts = {c: annual("gov_10a_exp", geo=GEO, na_item="TE", unit="PC_GDP",
                       sector="S13", cofog99=c, freq="A")
             for c in ("GF02", "GF03", "GF05", "GF06", "GF08")}
    # A summed line exists only in years where EVERY part is published —
    # a missing division is a hole, never a zero folded into the sum.
    def summed(codes: tuple[str, ...]) -> dict[int, float]:
        common = set.intersection(*(set(parts[c]) for c in codes))
        return {y: sum(parts[c][y] for c in codes) for y in common}

    cofog["defence_order"] = summed(("GF02", "GF03"))
    cofog["other"] = summed(("GF05", "GF06", "GF08"))
    cofog["total"] = annual("gov_10a_exp", geo=GEO, na_item="TE",
                            unit="PC_GDP", sector="S13", cofog99="TOTAL",
                            freq="A")
    check("COFOG social protection 2024 %GDP",
          cofog["social_protection"].get(2024), 21.3)
    order = ["social_protection", "health", "general_services", "education",
             "economic_affairs", "defence_order", "other", "total"]
    write("fiscal/spending_by_function_from_estat.csv",
          rows(years, {k: cofog[k] for k in order}, dec=2))

    # ---- investment: three concepts, kept apart ----------------------
    gfcf_pct = {y: gfcf[y] / nominal[y] * 100 for y in gfcf if y in nominal}
    write("fiscal/investment_from_estat.csv",
          rows(years, {"gfcf_eurbn": {y: v / 1000 for y, v in gfcf.items()},
                       "gfcf_pct_gdp": gfcf_pct,
                       "gov_gfcf_pct_gdp": gov_gfcf}, dec=2))

    # ---- trade in the national accounts (the customs chapter is pending)
    exports = annual("nama_10_gdp", geo=GEO, na_item="P6",
                     unit="CP_MEUR", freq="A")
    imports = annual("nama_10_gdp", geo=GEO, na_item="P7",
                     unit="CP_MEUR", freq="A")
    write("trade/trade_from_estat.csv",
          rows(years, {"exports_eurbn": {y: v / 1000 for y, v in exports.items()},
                       "imports_eurbn": {y: v / 1000 for y, v in imports.items()}},
               dec=2))

    # ---- labour market ------------------------------------------------
    # une_rt_a starts 2009 for Italy: 2006-2008 are blank in the source,
    # carried as blanks. The only 2006-2008 coverage is ISTAT's
    # old-regulation RFL — a separate file, never spliced into this one.
    unemp = annual("une_rt_a", geo=GEO, unit="PC_ACT", sex="T",
                   age="Y15-74", freq="A")
    if any(y in unemp for y in (2006, 2007, 2008)):
        raise RuntimeError("une_rt_a now covers 2006-2008 for IT — "
                           "the documented hole changed; re-verify before "
                           "drawing across the ISTAT old-regulation seam")
    write("macro/unemployment_from_estat.csv",
          rows(years, {"estat": unemp}, dec=1))

    # ---- prices: the HICP, which is NOT ISTAT's NIC -------------------
    hicp = annual("prc_hicp_aind", geo=GEO, unit="RCH_A_AVG",
                  coicop="CP00", freq="A")
    write("macro/hicp_from_estat.csv", rows(years, {"hicp": hicp}, dec=2))

    # ---- the 10-year benchmark yield (the BTP) ------------------------
    y10 = annual("irt_lt_mcby_a", geo=GEO, freq="A")
    write("markets/yield_10y_from_estat.csv", rows(years, {"yield_10y": y10},
                                                   dec=2))

    # ---- inequality and poverty, EU-SILC ------------------------------
    # ilc_di12's dimension is statinfo=GINI_HND; indic_il is HTTP 400.
    gini = annual("ilc_di12", geo=GEO, age="TOTAL", statinfo="GINI_HND",
                  freq="A")
    arop = annual("ilc_li02", geo=GEO, unit="PC", sex="T", age="TOTAL",
                  statinfo="MED_EI", rskpovth="B_60", freq="A")
    write("social/gini_from_estat.csv", rows(years, {"silc": gini}, dec=1))
    write("social/poverty_from_estat.csv", rows(years, {"arop60": arop},
                                                dec=1))

    # ---- observed demography (the national series comes from ISTAT) ---
    pop = annual("demo_gind", geo=GEO, indic_de="JAN", freq="A")
    births = annual("demo_gind", geo=GEO, indic_de="LBIRTH", freq="A")
    deaths = annual("demo_gind", geo=GEO, indic_de="DEATH", freq="A")
    tfr = annual("demo_find", geo=GEO, indic_de="TOTFERRT", freq="A")
    check("population 1-Jan-2025", pop.get(2025), 58943464, tol=1)
    check("TFR 2024", tfr.get(2024), 1.18, tol=0.005)
    write("social/demography_from_estat.csv",
          rows(years, {"population": pop, "births": births,
                       "deaths": deaths, "tfr": tfr},
               dec={"population": 0, "births": 0, "deaths": 0, "tfr": 2}))

    # ---- migration: the harmonised suite, both definitions ------------
    imm = migration("migr_imm1ctz", "citizen", "by_citizenship", agedef=True)
    imm_birth = migration("migr_imm3ctb", "c_birth", "by_birth", agedef=True)

    # Italy transmits ONE immigration flow under both definitions: the
    # totals are identical on the two cuts (no EM/EMCR-style splice like
    # Spain's). Assert that still holds — if a revision breaks it, the
    # chapter's "no totals gap" story breaks with it.
    overlap = sorted(set(imm["by_citizenship_total"])
                     & set(imm_birth["by_birth_total"]))
    if not overlap:
        raise RuntimeError("migr_imm1ctz/migr_imm3ctb: no overlapping years")
    diff = {y: imm["by_citizenship_total"][y] - imm_birth["by_birth_total"][y]
            for y in overlap}
    bad = {y: d for y, d in diff.items() if d != 0}
    if bad:
        raise RuntimeError(
            f"immigration totals diverge between the citizenship and "
            f"birth cuts {bad} — Italy's no-splice finding changed; "
            f"re-verify before drawing")
    print(f"  check no EM/EMCR splice: totals identical {overlap[0]}-"
          f"{overlap[-1]} ok ({len(overlap)} years)")
    write("migration/immigration_from_estat.csv",
          rows(years, {**imm, **imm_birth}, dec=0))

    emi = migration("migr_emi1ctz", "citizen", "by_citizenship", agedef=True)
    write("migration/emigration_from_estat.csv", rows(years, emi, dec=0))

    # Stocks: the foreign aggregate is FOR_STLS on the citizenship cut
    # (FOR is a well-formed EMPTY cube) and FOR on the country-of-birth
    # cut — migration() names the right one per dataset and fails loudly
    # on empty.
    stock = migration("migr_pop1ctz", "citizen", "by_citizenship")
    stock_birth = migration("migr_pop3ctb", "c_birth", "by_birth")
    check("foreign-citizen stock 1-Jan-2025",
          stock["by_citizenship_foreign"].get(2025), 5371251, tol=1)
    check("foreign-born stock 1-Jan-2025",
          stock_birth["by_birth_foreign"].get(2025), 6928045, tol=1)
    write("migration/stock_from_estat.csv",
          rows(years, {**stock, **stock_birth}, dec=0))

    # Asylum: unit=PER — with unit=NR the cube comes back silently empty.
    # Applications are not arrivals, grants or people present.
    asy = annual("migr_asyappctza", geo=GEO, unit="PER", citizen="TOTAL",
                 applicant="TOTAL", sex="T", age="TOTAL", freq="A")
    asy_first = annual("migr_asyappctza", geo=GEO, unit="PER",
                       citizen="TOTAL", applicant="FRST", sex="T",
                       age="TOTAL", freq="A")
    if not asy:
        raise RuntimeError("migr_asyappctza: empty result")
    check("asylum applications 2024", asy.get(2024), 158605, tol=1)
    write("migration/asylum_from_estat.csv",
          rows(years, {"applications": asy, "first_time": asy_first},
               dec=0))

    # First residence permits: unit=PER, same empty-cube trap.
    permits = annual("migr_resfirst", geo=GEO, unit="PER", citizen="TOTAL",
                     reason="TOTAL", duration="TOTAL", freq="A")
    if not permits:
        raise RuntimeError("migr_resfirst: empty result")
    check("first permits 2024", permits.get(2024), 346411, tol=1)
    write("migration/permits_from_estat.csv",
          rows(years, {"first_permits": permits}, dec=0))

    # Acquisitions of citizenship: the naturalisation flow that moves the
    # citizenship-cut stock without anybody moving.
    acq = annual("migr_acq", geo=GEO, unit="NR", citizen="TOTAL", sex="T",
                 age="TOTAL", agedef="REACH", freq="A")
    if not acq:
        raise RuntimeError("migr_acq: empty result")
    check("naturalisations 2024", acq.get(2024), 217448, tol=1)
    write("migration/naturalisation_from_estat.csv",
          rows(years, {"acquisitions": acq}, dec=0))

    if CHECKS:
        raise RuntimeError(
            "spot checks failed: " + "; ".join(
                f"{n} got {g} want {w}" for n, g, w, _ in CHECKS))
    print("Done. Diff the *_from_estat.csv sidecars before adopting.")


if __name__ == "__main__":
    main()
