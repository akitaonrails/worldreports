#!/usr/bin/env python3
"""Fetch official annual series from the Argentine national series API.

Usage:  python3 scripts/fetch_datos_gob.py

`apis.datos.gob.ar/series` is the republic's single time-series gateway: it
republishes INDEC, BCRA, the Secretaría de Hacienda and the Ministerio de
Seguridad under stable ids, so one fetcher covers most of this atlas. Every
response is cached under cache/series/, so re-running is cheap and an upstream
outage leaves the committed CSVs untouched.

Values are fetched **uncollapsed** and aggregated to years here. The API can
collapse a series itself, but it silently drops a year it considers
incomplete — which deletes 2026 from every monthly series, the one year this
atlas most needs to show as partial. Aggregating locally also yields the
period count per year, so `to_year` can refuse to report eight months of
exports as an annual total.

Outputs are `*_check.csv` sidecars next to the curated CSVs: live data never
overwrites a curated number. Diff the sidecar and copy across what you accept.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "series"
DATA = ROOT / "data"

API = "https://apis.datos.gob.ar/series/api/series/"
# the gateway 403s a default urllib agent
UA = {"User-Agent": "argentina-reports/1.0 (+https://github.com/AkitaOnRails)"}

YEAR_FROM, YEAR_TO = 2006, 2026

# How many periods a complete year has, by the frequency the series carries.
PERIODS = {"month": 12, "quarter": 4, "semester": 2, "year": 1}


# ------------------------------------------------------------- aggregation
def to_year(points: dict[str, float], how: str, freq: str,
            require_full: bool = True) -> tuple[dict[int, float], dict[int, float]]:
    """Collapse dated points to (complete years, partial years).

    `points` is {ISO date -> value} as the API serves it. `how` is one of:

      sum   annual total of a flow — only meaningful over a whole year
      avg   annual average of a rate
      eop   the last reading of the year: a stock, an index, a closing price

    A year missing periods is returned in the second dict instead of the
    first, so a caller can print it as partial rather than as a total. An
    end-of-period reading is never partial in that sense — the latest reading
    of a stock is a real reading — so `require_full` is ignored for "eop".
    """
    if how not in ("sum", "avg", "eop"):
        raise ValueError(f"unknown aggregation: {how}")
    want = PERIODS.get(freq)
    if want is None:
        raise ValueError(f"unknown frequency: {freq}")

    buckets: dict[int, list[tuple[str, float]]] = {}
    for date, value in points.items():
        if value is None:
            continue
        buckets.setdefault(int(date[:4]), []).append((date, value))

    full: dict[int, float] = {}
    partial: dict[int, float] = {}
    for year, rows in buckets.items():
        rows.sort()
        values = [v for _, v in rows]
        if how == "sum":
            agg = sum(values)
        elif how == "avg":
            agg = sum(values) / len(values)
        else:
            agg = values[-1]
        complete = len(rows) >= want or how == "eop" or not require_full
        (full if complete else partial)[year] = agg
    return full, partial


def semesters(points: dict[str, float]) -> dict[int, dict[int, float]]:
    """Collapse the EPH poverty series to {year: {1: s1, 2: s2}}.

    **The poverty series is dated at the day after the half it describes
    ends**, not at its start: 2024-07-01 is the first half of 2024 and
    2025-01-01 is the second half of 2024. Reading those dates as the year
    printed in them shifts the series six months and reports the 52.9%
    peak — the first half of 2024, against a true second half of 38.1% — as
    the wrong half of the wrong trend.

    This convention is **not** the gateway's. The monthly IPC is dated at
    the start of its month (2016-12-01 = December 2016 = 100.0) and the
    quarterly Gini at the start of its quarter (2024-01-01 = 0.467, the
    post-devaluation first quarter). Poverty, from the same survey as the
    Gini and published in the same report, is the one that is offset.
    Nothing in the metadata says so; the only way to find it is to know
    what a published figure should be and notice it is in the wrong cell.
    Check the convention per series, not per API.

    The two readings of a year are returned separately because INDEC quotes
    them separately; a caller that wants one number per year averages them,
    and should say so on the chart.
    """
    out: dict[int, dict[int, float]] = {}
    for date, value in points.items():
        if value is None:
            continue
        year, month = int(date[:4]), int(date[5:7])
        if month == 7:
            out.setdefault(year, {})[1] = value
        elif month == 1:
            out.setdefault(year - 1, {})[2] = value
        else:
            raise ValueError(f"not a half-yearly date: {date}")
    return out


def half_columns(sid: str, label: str, factor: float = 1.0
                 ) -> tuple[dict[int, float], dict[int, float], dict[int, float]]:
    """(first half, second half, average) of a half-yearly series."""
    halves = semesters(fetch(sid))
    s1 = {y: h[1] * factor for y, h in halves.items() if 1 in h}
    s2 = {y: h[2] * factor for y, h in halves.items() if 2 in h}
    avg = {y: sum(h.values()) / len(h) * factor for y, h in halves.items()}
    only = sorted(y for y, h in halves.items() if len(h) == 1)
    tail = f"  one half only: {only}" if only else ""
    print(f"  {label:<24} {len(halves):>3} years "
          f"{min(halves, default='-')}-{max(halves, default='-')}{tail}")
    return s1, s2, avg


def drop_zeros(points: dict[str, float], label: str) -> dict[str, float]:
    """Treat an exact 0.0 as "not measured" for a price or a rate.

    Several BCRA rate series stop being measured and then keep being
    published as 0.0 for years: the overdraft rate's last real reading is
    December 2016 and the 5-10 year mortgage rate's is June 2017, yet both
    serve a clean zero every month through 2026. Nothing in the payload
    distinguishes that from a rate that genuinely fell to zero — only the
    knowledge that no Argentine mortgage has ever been free does. A rate of
    exactly 0.0 is therefore dropped, and the caller is told where the real
    series ended.
    """
    kept = {d: v for d, v in points.items() if v}
    if kept and len(kept) < len(points):
        print(f"  {label:<24} real data ends {max(kept)[:7]} "
              f"({len(points) - len(kept)} zero-filled periods dropped)")
    return kept


# --------------------------------------------------------------- transport
def fetch(sid: str) -> dict[str, float]:
    """Every published point of one series, {ISO date -> value}, cached."""
    cache_file = CACHE / f"{sid.replace('/', '_')}.json"
    if cache_file.exists():
        payload = json.loads(cache_file.read_text())
    else:
        CACHE.mkdir(parents=True, exist_ok=True)
        params = {"ids": sid, "format": "json", "limit": 5000,
                  "start_date": f"{YEAR_FROM - 1}-01-01"}
        url = API + "?" + urllib.parse.urlencode(params)
        payload = None
        for attempt in range(4):
            try:
                req = urllib.request.Request(url, headers=UA)
                with urllib.request.urlopen(req, timeout=120) as r:
                    payload = json.load(r)
                break
            except Exception as e:  # noqa: BLE001
                print(f"  [{sid}] attempt {attempt + 1}: {e}", file=sys.stderr)
                time.sleep(3 * (attempt + 1))
        if payload is None:
            print(f"  [{sid}] GIVING UP", file=sys.stderr)
            return {}
        cache_file.write_text(json.dumps(payload))
    return {row[0]: row[1] for row in payload.get("data", [])
            if row[1] is not None}


def annual(sid: str, how: str, freq: str, label: str = "") -> dict[int, float]:
    """One series as {year -> value}, partial years included but reported."""
    full, partial = to_year(fetch(sid), how, freq)
    both = dict(full)
    both.update(partial)
    if both:
        span = f"{min(both)}-{max(both)}"
        tail = f"  partial: {sorted(partial)}" if partial else ""
        print(f"  {label or sid:<24} {len(both):>3} years {span}{tail}")
    else:
        print(f"  {label or sid:<24} EMPTY ({sid})", file=sys.stderr)
    return both


def complete_only(sid: str, how: str, freq: str, label: str = "") -> dict[int, float]:
    """Only years the source has published in full — for annual totals that
    would read as a collapse if a partial year were plotted as one."""
    full, _ = to_year(fetch(sid), how, freq)
    print(f"  {label or sid:<24} {len(full):>3} complete years")
    return full


# ------------------------------------------------------------------ output
def write(rel: str, header: str, rows: list[str]) -> None:
    path = DATA / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join([header] + rows) + "\n")
    print(f"  -> data/{rel}")


def fmt(v, spec: str) -> str:
    return format(v, spec) if v is not None else ""


def scale(d: dict[int, float], factor: float) -> dict[int, float]:
    return {y: v * factor for y, v in d.items()}


def table(rel: str, columns: list[tuple[str, dict[int, float], str]]) -> None:
    """One row per year of the window, one column per named series."""
    rows = []
    for y in range(YEAR_FROM, YEAR_TO + 1):
        rows.append(",".join([str(y)]
                             + [fmt(d.get(y), spec) for _, d, spec in columns]))
    write(rel, "year," + ",".join(name for name, _, _ in columns), rows)


# ------------------------------------------------------------------ series
# INDEC — Producto Interno Bruto en dólares, PIB per cápita y población
GDP_ARS = "9.1_PPC_2004_A_22"        # PIB, millones de pesos corrientes
GDP_USD = "9.1_PDPC_2004_A_30"       # PIB, millones de dólares corrientes
GDP_PC = "9.1_PPCDC_2004_A_33"       # PIB per cápita, dólares corrientes
POP = "9.1_POB_2004_A_9"             # población
GDP_K = "6.1_PIBPM_2004_A_38"        # PIB a precios constantes de 2004
GDP_K_Q = "6.2_PIBPM_2004_T_38"      # idem, trimestral (extiende a 2026)

IPC = "145.3_INGNACNAL_DICI_M_15"    # IPC nacional, nivel general, dic-2016=100
UNEMP = "45.1_ECTDT_0_A_33"          # EPH continua, tasa de desempleo, anual
UNEMP_Q = "45.2_ECTDT_0_T_33"        # idem trimestral (extiende a 2026)
SMVM = "57.1_SMVMM_0_M_34"           # salario mínimo vital y móvil, mensual
RESERVES = "92.1_RID_0_0_32"         # reservas internacionales BCRA, US$ mn
FX_VAL = "92.1_TCV_0_0_21"           # tipo de cambio de valuación, $/US$

POVERTY = "64.2_POBLACION_NUA_0_0_34_74"   # EPH, población bajo la línea, %
GINI = "65.1_CGI_0_0_21"                   # Gini del ingreso per cápita familiar

HOM_COUNT = "snic_1_victimas_arg"          # víctimas de homicidios dolosos
HOM_RATE = "t_snic_1_victimas_arg"         # tasa por 100.000

# BCRA — crédito, depósitos y tasas. "Series históricas de estadísticas
# monetarias" (dataset 174) is monthly and alive; the rate series inside it
# are not all alive, which drop_zeros() exists to handle.
LOANS = "174.1_PTAMOS_TAL_0_0_33"          # préstamos al sector privado, $ mn
DEPOSITS = "174.1_DSITOS_TAL_0_0_33"       # depósitos del sector privado, $ mn
RATE_PF = "174.1_T_INTERD_0_0_41"          # plazo fijo 30-59 días, % anual
RATE_MORTGAGE = "174.1_T_INTERS_0_0_56"    # hipotecarios 5-10 años — muere 2017
RATE_OVERDRAFT = "174.1_T_INTERO_II_0_0_57"  # adelantos en c/c — muere 2016
# "Principales Indicadores del Sistema Financiero" (dataset 332), annual.
# Both are percentages despite the catalogue declaring them millones de pesos.
NPL = "332.1_BANCOS_PRIADA__51"            # irregularidad de la cartera privada
CREDIT_SHARE = "332.1_BANCOS_PRIADO__43"   # crédito privado / activo bancario

EXPORTS = "74.3_IET_0_M_16"                # ICA, exportaciones, US$ mn
IMPORTS = "74.3_IIT_0_M_25"                # ICA, importaciones, US$ mn
# ICA, exportaciones por rubro. The four rubros partition total exports by
# definition, which is how "moi" is recovered: the MOI ids are listed in the
# catalogue but the gateway serves them empty at every frequency, so it is
# computed as the residual rather than left out of the panel.
RUBROS = {
    "primarios": ("74.3_IEPP_0_M_35", "month"),
    "moa": ("74.3_IEMOA_0_M_48", "month"),
    "combustibles": ("74.1_IECE_0_A_35", "year"),  # only the annual id has data
}
MOI_IS_RESIDUAL = True

# Secretaría de Hacienda — Esquema Ahorro-Inversión-Financiamiento del SPNF.
# Three incompatible methodologies, kept as three columns and never spliced.
# Frequency is declared, never inferred from the id: the 2017-methodology
# series is monthly and its id carries no "_M_" marker, so a sniffing rule
# read it as annual and reported one December month as the whole year — a
# +1.8% surplus came out as a -0.2% deficit.
PRIMARY = {
    "m1993": ("379.1_SUPERAVIT_006__28_89", "year"),    # 1993-2006 methodology
    "m2007": ("379.2_SUPERAVIT_014__28_63", "year"),    # 2007-2014 methodology
    "m2017": ("379.9_SUPERAVIT_017__23_94", "month"),   # 2015- methodology
}

# Secretaría de Política Económica — Gasto Público Consolidado, nación, % PIB
SPEND = {
    "prevision": "451.4_GPN_PREVISPIB_0_0_24_69",
    "salud": "451.4_GPN_ATENCIPIB_0_0_22_87",
    "salud_obras": "451.4_GPN_OBRAS_PIB_0_0_28_7",
    "salud_inssjp": "451.4_GPN_INSSJYPIB_0_0_21_94",
    "educacion_basica": "451.4_GPN_EDUCACPIB_0_0_24_66",
    "educacion_superior": "451.4_GPN_EDUCACPIB_0_0_31_0",
    "asistencia": "451.4_GPN_PROMOCPIB_0_0_35_70",
    "asignaciones": "451.4_GPN_ASIGNAPIB_0_0_31_8",
    "defensa_seguridad": "451.4_GPN_DEFENSPIB_0_0_25_96",
    "energia": "451.4_GPN_ENERGIPIB_0_0_27_42",
    "transporte": "451.4_GPN_TRANSPPIB_0_0_18_37",
    "funcionamiento": "451.4_GPN_FUNCIOPIB_0_0_29_33",
    "deuda": "451.4_GPN_SERVICPIB_0_0_31_93",
    "total": "451.4_GPN_PIBPIB_0_0_7_95",
}

# Recursos tributarios nacionales, $ millones. National taxes only: the
# provinces levy Ingresos Brutos and the municipalities their tasas on top,
# so this is not the whole tax burden. Only the monthly ids return data —
# the annual ones are listed in the catalogue but serve nothing.
TAX = {
    "total": "142.3_TOTAL_2001_M_26",
    "export_duties": "142.3_DEREC_2001_M_20",
    "ganancias": "142.3_GANAN_2001_M_9",
}


# ------------------------------------------------------------------- build
def build_gdp() -> None:
    print("INDEC — Cuentas Nacionales (PIB, población)")
    usd = annual(GDP_USD, "eop", "year", "PIB US$ mn")
    pc = annual(GDP_PC, "eop", "year", "PIB pc US$")
    pop = annual(POP, "eop", "year", "población")
    ars = annual(GDP_ARS, "eop", "year", "PIB $ mn")

    # The annual accounts stop a year behind the quarterly ones. Four
    # quarters at constant prices are the same aggregate, so they extend the
    # growth rate without changing its definition; an incomplete year would
    # understate growth badly, so only complete ones are taken.
    const = annual(GDP_K, "eop", "year", "PIB const.")
    for year, value in complete_only(GDP_K_Q, "sum", "quarter", "PIB const. T").items():
        const.setdefault(year, value)

    growth = {y: (const[y] / const[y - 1] - 1) * 100
              for y in const if (y - 1) in const}
    table("macro/gdp_check.csv", [
        ("usd_bn", scale(usd, 1 / 1000), ".1f"),
        ("real_growth", growth, ".1f"),
        ("gdp_per_capita_usd", pc, ".0f"),
        ("population_mn", scale(pop, 1 / 1e6), ".2f"),
        ("ars_bn", scale(ars, 1 / 1000), ".1f"),
    ])


def build_prices_and_rates() -> None:
    print("INDEC — IPC; EPH; BCRA — reservas y tipo de cambio")
    index = annual(IPC, "eop", "month", "IPC dic=100")
    inflation = {y: (index[y] / index[y - 1] - 1) * 100
                 for y in index if (y - 1) in index}
    table("macro/ipc_check.csv", [("official", inflation, ".1f")])

    # the EPH rates arrive as fractions (0.0739), not percentages
    unemp = annual(UNEMP, "avg", "year", "desempleo")
    for year, value in complete_only(UNEMP_Q, "avg", "quarter", "desempleo T").items():
        unemp.setdefault(year, value)
    table("macro/unemployment_check.csv", [("value", scale(unemp, 100), ".1f")])

    table("macro/minimum_wage_check.csv",
          [("value", annual(SMVM, "eop", "month", "SMVM"), ".0f")])
    table("macro/reserves_check.csv",
          [("eop_usbi", scale(annual(RESERVES, "eop", "month", "reservas"),
                              1 / 1000), ".2f")])

    fx = fetch(FX_VAL)
    avg, _ = to_year(fx, "avg", "month", require_full=False)
    eop, _ = to_year(fx, "eop", "month")
    table("macro/dollar_check.csv",
          [("official_avg", avg, ".2f"), ("official_eop", eop, ".2f")])


def build_social() -> None:
    print("INDEC — pobreza, Gini; Ministerio de Seguridad — SNIC")
    # Both come off the EPH twice a year and both are dated at the end of
    # the half they describe — see semesters(). Each half is written out as
    # its own column rather than collapsed, because INDEC reports them that
    # way and because the gap between them is sometimes the whole story:
    # poverty was 52.9% in the first half of 2024 and 38.1% in the second.
    # 2008-2015 stays empty on purpose: the intervened INDEC's figures were
    # withdrawn by the 2016 statistical emergency.
    s1, s2, avg = half_columns(POVERTY, "pobreza", 100)
    table("social/poverty_check.csv",
          [("s1", s1, ".1f"), ("s2", s2, ".1f"), ("avg", avg, ".1f")])
    # The Gini is quarterly and dated normally — see semesters() for why
    # that is worth saying out loud next to a series that is not.
    table("social/gini_check.csv",
          [("indec", annual(GINI, "avg", "quarter", "Gini"), ".4f")])
    table("social/homicides_check.csv", [
        ("count", annual(HOM_COUNT, "eop", "year", "homicidios"), ".0f"),
        ("rate", annual(HOM_RATE, "eop", "year", "tasa"), ".2f"),
    ])


def build_trade() -> None:
    print("INDEC — Intercambio Comercial Argentino")
    exp = annual(EXPORTS, "sum", "month", "exportaciones")
    imp = annual(IMPORTS, "sum", "month", "importaciones")
    balance = {y: exp[y] - imp[y] for y in exp if y in imp}
    table("trade/trade_check.csv", [
        ("exports", scale(exp, 1 / 1000), ".1f"),
        ("imports", scale(imp, 1 / 1000), ".1f"),
        ("balance", scale(balance, 1 / 1000), ".1f"),
    ])

    by_rubro: dict[str, dict[int, float]] = {}
    for name, (sid, freq) in RUBROS.items():
        by_rubro[name] = annual(sid, "eop" if freq == "year" else "sum",
                                freq, name)
    if MOI_IS_RESIDUAL:
        named = set.intersection(*(set(d) for d in by_rubro.values()))
        by_rubro["moi"] = {
            y: exp[y] - sum(by_rubro[n][y] for n in RUBROS)
            for y in sorted(named & set(exp))}
        print(f"  moi (residual)           {len(by_rubro['moi']):>3} years")

    rows = []
    for name in ("primarios", "moa", "moi", "combustibles"):
        for year, value in sorted(by_rubro.get(name, {}).items()):
            if YEAR_FROM <= year <= YEAR_TO:
                rows.append(f"{year},{name},{value / 1000:.1f}")
    rows.sort(key=lambda r: (int(r.split(",")[0]), r.split(",")[1]))
    write("trade/exports_rubros_check.csv", "year,rubro,usbi", rows)


def build_fiscal() -> None:
    print("Secretaría de Hacienda — SPNF; Gasto Público Consolidado")
    # The AIF publishes the primary balance in pesos of the year, which is
    # unreadable across a span where the price level rose 1,200-fold. Divided
    # by the same year's nominal GDP it becomes the ratio every commentary
    # quotes (2024: +1.8% of GDP). 2026 has no annual GDP yet, so its ratio
    # stays empty while the peso figure is still written.
    gdp_ars = annual(GDP_ARS, "eop", "year", "PIB $ mn")
    cols = []
    for name, (sid, freq) in PRIMARY.items():
        pesos = annual(sid, "sum" if freq == "month" else "eop", freq, name)
        pct = {y: v / gdp_ars[y] * 100 for y, v in pesos.items() if y in gdp_ars}
        cols.append((name, pct, ".2f"))
    table("fiscal/primary_result_check.csv", cols)

    table("fiscal/spending_by_function_check.csv",
          [(name, annual(sid, "eop", "year", name), ".3f")
           for name, sid in SPEND.items()])

    cols = []
    for name, sid in TAX.items():
        pesos = annual(sid, "sum", "month", name)
        cols.append((f"{name}_pct_gdp",
                     {y: v / gdp_ars[y] * 100 for y, v in pesos.items()
                      if y in gdp_ars}, ".2f"))
    table("fiscal/tax_revenue_check.csv", cols)


def build_credit() -> None:
    """How much credit exists, what it costs, and how much of it goes bad.

    Argentina's banking system is small rather than fragile: private credit
    has spent this whole window between roughly 5% and 15% of GDP, against
    50-70% in Chile or Brazil. The interesting movements are therefore in
    both directions — the collapse to about 4% of GDP in 2023 and the sharp
    expansion through 2024-25 are both large in relative terms and small in
    absolute ones, and a chart that does not say so invites the reader to
    read an Argentine credit boom as a Chilean one.

    The deposit rate is nominal, which across this window means almost
    nothing on its own: 95% a year was a deeply negative return in 2023.
    The real rate is computed against the same inflation series the price
    panel uses, with the INDEC gap left empty rather than filled from the
    intervened index.
    """
    print("BCRA — crédito al sector privado, depósitos, tasas, irregularidad")
    gdp_ars = annual(GDP_ARS, "eop", "year", "PIB $ mn")

    loans = annual(LOANS, "eop", "month", "préstamos priv.")
    deposits = annual(DEPOSITS, "eop", "month", "depósitos priv.")
    pct = lambda d: {y: v / gdp_ars[y] * 100 for y, v in d.items() if y in gdp_ars}

    rate_pf, _ = to_year(fetch(RATE_PF), "avg", "month", require_full=False)
    mortgage, _ = to_year(drop_zeros(fetch(RATE_MORTGAGE), "hipotecarios"),
                          "avg", "month", require_full=False)
    overdraft, _ = to_year(drop_zeros(fetch(RATE_OVERDRAFT), "adelantos"),
                           "avg", "month", require_full=False)

    # Real deposit rate, Fisher-exact, against December-to-December IPC.
    # Only the years the official national index covers; the intervened
    # decade has no denominator this atlas is willing to divide by.
    ipc = annual(IPC, "eop", "month", "IPC dic.")
    inflation = {y: (ipc[y] / ipc[y - 1] - 1) * 100
                 for y in ipc if (y - 1) in ipc}
    real_pf = {y: ((1 + rate_pf[y] / 100) / (1 + inflation[y] / 100) - 1) * 100
               for y in rate_pf if y in inflation}

    table("macro/credit_check.csv", [
        ("loans_pct_gdp", pct(loans), ".2f"),
        ("deposits_pct_gdp", pct(deposits), ".2f"),
        ("rate_timedeposit", rate_pf, ".1f"),
        ("rate_timedeposit_real", real_pf, ".1f"),
        ("rate_mortgage", mortgage, ".1f"),
        ("rate_overdraft", overdraft, ".1f"),
    ])
    table("macro/credit_quality_check.csv", [
        ("npl_private_pct", annual(NPL, "eop", "year", "irregularidad"), ".2f"),
        ("credit_share_assets_pct",
         annual(CREDIT_SHARE, "eop", "year", "crédito/activo"), ".2f"),
    ])

def main() -> None:
    build_gdp()
    build_prices_and_rates()
    build_social()
    build_trade()
    build_fiscal()
    build_credit()
    print("Done. Sidecars written as *_check.csv — diff before adopting.")


if __name__ == "__main__":
    main()
