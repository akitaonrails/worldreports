#!/usr/bin/env python3
"""Refresh the INE Portugal series into sidecar CSVs.

Usage:  python3 -I countries/portugal/fetch/fetch_ine.py [--refresh]

The Instituto Nacional de Estatística serves every indicator of its
Base de Dados through one keyless JSON API:

  data      https://www.ine.pt/ine/json_indicador/pindica.jsp
              ?op=2&varcd={code}&Dim1=…&Dim2=…&lang=PT
  metadata  https://www.ine.pt/ine/json_indicador/pindicaMeta.jsp
              ?varcd={code}&lang=PT

The `varcd` is the Base de Dados' `indOcorrCod`. Indicators used here:

  0013428   GDP at current prices, quarterly, base 2021, € millions
  0014144   GDP real growth, annual, base 2021 — REGIONAL accounts
            (Contas económicas regionais), an older vintage; see gdp()
  0014649   IPC, 12-month average rate (December = the annual average)
  0014647   IPC, y/y rate, monthly
  0012173   unemployment rate, LFS Série 2021, annual (2011–)
  0006191   unemployment rate, LFS Série 2011, annual (2011–2020)
  0007976   unemployment rate 16–74, monthly (centred 3-month windows)
  0004167   resident population, 31 December, REVISED vintage
  0008086   live births, NUTS-2013 (2011–2023)
  0012436   live births, NUTS-2024, annual (2021–)
  0012094   live births, NUTS-2024, monthly (2026–)
  0008834   deaths, NUTS-2013, by urban typology (2011–2023)
  0001293   total fertility rate
  0001724   life expectancy at birth, three-year tables
  0008206   deaths by cause, European shortlist, NUTS-2013 (1980–2022)
  0013166   deaths by cause, European shortlist, NUTS-2024 (2022–2024)
  0008074   recorded-crime rate ‰, DGPJ, NUTS-2013 (2011–2022)
  0012260   recorded-crime rate ‰, DGPJ, NUTS-2024 (2021–2025)
  0004212   Gini coefficient, ICOR (EU-SILC)
  0009821   at-risk-of-poverty rate, NUTS-2013
  0014079   at-risk-of-poverty rate, NUTS-2024
  0004172   goods exports, monthly, by destination × CPA-2008
  0004169   goods imports, monthly, by origin × CPA-2008
  0006055   permanent immigrants, by nationality
  0006050   permanent emigrants, by sex
  0013179   net migration, NUTS-2024
  0008269   net migration, NUTS-2013
  0009107   foreign population with legal residence, NUTS-2013
  0013220   idem, NUTS-2024
  0010247   idem, by nationality (top ten + rest)

Things this API will do to you:

**A bad request is HTTP 200 JSON with `Sucesso.Falso`.** An invalid
dimension code ("Código(s) em Dim3 não válido(s)") arrives as a
well-formed payload with no `Dados`; nothing is cached or parsed unless
`Sucesso.Verdadeiro` is present.

**Leaving Dim1 out returns only the LATEST period**, not the series. Every
call lists its period codes explicitly, taken from the metadata:
annual `S7A{year}`, quarterly `S5A{year}{q}`, monthly `S3A{year}{mm}`,
three-year tables `S16A{y0}{y1}`. The data comes back keyed by the period's
DESCRIPTION ("Dezembro de 2024", "1.º Trimestre de 2024"), which is mapped
back to the code through the same metadata.

**Geography "T" is not geography "PT".** The vital-statistics and
cause-of-death cubes have both a "Total" (T) and a "Portugal" (PT)
category in the place-of-residence dim; T also counts deaths and births of
people resident abroad or of unknown residence. 2022 assaults: T = 98,
PT = 97. Every series here is the PT (resident) one.

**All-causes `T-LES`** appears in the cause-of-death metadata but the data
endpoint rejects it — all-cause totals come from 0008834, which has no
total category in its urban-typology dim (sum APU+AMU+APR).

**40,000 cells per call.** Period lists are chunked and every call's cell
count is checked before it is sent.

**Series breaks are kept as separate columns, never spliced:** births
NUTS-2013 vs NUTS-2024, causes of death 0008206 vs 0013166 (2022 on both),
crime 0008074 vs 0012260 (2021–2022 on both), unemployment Série 2021 vs
Série 2011 vs the long monthly run, net migration and the foreign-resident
stock NUTS-2013 vs NUTS-2024, poverty NUTS-2013 vs NUTS-2024.

**THE VINTAGE TRAP.** On 2026-06-22 INE revised population 2021–2024
upward (end-2024 = 11,387,222) on an administrative-data methodology, and
the migration flows with it. The INE population and flow series here are
the REVISED vintage; Eurostat migr_* and the World Bank are pre-revision.
The CSV comments carry the vintage map; nothing here is joined to another
publisher's file.

Outputs are `_from_ine.csv` sidecars. Nothing here overwrites a curated
file. `--refresh` ignores the cache and re-reads everything live.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache"

DATA_URL = "https://www.ine.pt/ine/json_indicador/pindica.jsp"
META_URL = "https://www.ine.pt/ine/json_indicador/pindicaMeta.jsp"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) worldreports-fetch"}
Y0, Y1 = 2006, 2026
CELL_CAP = 40_000
REFRESH = "--refresh" in sys.argv[1:]

VINTAGE_MAP = [
    "VINTAGE MAP (INE revision of 2026-06-22 — never mix vintages):",
    "  INE 0004167 population, 0006055 immigration, 0006050 emigration,",
    "  0013179 net migration = REVISED (administrative base from 2021).",
    "  Eurostat migr_* = PRE-revision (immigration stops at 2023);",
    "  Eurostat demo_gind = revised; World Bank population = pre-revision.",
    "  INE and Eurostat flows agree exactly through 2020; the 2021 step is",
    "  methodology, not migration — mark the seam, never draw one line.",
]


# ---------------------------------------------------------------- transport

def _fetch_json(url: str, cache_file: Path) -> list:
    """GET a JSON document; cache it only once the payload says Sucesso.

    A metadata response is a list holding one dict with `Dimensoes`; a data
    response holds `Sucesso.Verdadeiro` and `Dados`. Anything else — an
    HTML error page, `Sucesso.Falso` — raises with INE's own message.
    """
    if cache_file.exists() and not REFRESH:
        return json.loads(cache_file.read_text(encoding="utf-8"))
    CACHE.mkdir(exist_ok=True)
    last: Exception | None = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=300) as r:
                raw = r.read()
            payload = json.loads(raw.decode("utf-8"))
            break
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (attempt + 1))
    else:
        raise RuntimeError(f"ine {url}: {last}")
    if not isinstance(payload, list) or not payload \
            or not isinstance(payload[0], dict):
        raise RuntimeError(f"ine {url}: not an INE payload")
    head = payload[0]
    ok = head.get("Sucesso", {})
    if "Falso" in ok:
        msg = "; ".join(m.get("Msg", "?") for m in ok["Falso"])
        raise RuntimeError(f"ine {url}: Sucesso.Falso — {msg}")
    if "Dimensoes" not in head and "Verdadeiro" not in ok:
        raise RuntimeError(f"ine {url}: no Sucesso.Verdadeiro and no metadata")
    cache_file.write_text(json.dumps(payload, ensure_ascii=False),
                          encoding="utf-8")
    time.sleep(0.3)
    return payload


class Meta:
    """An indicator's metadata: its periods and each dimension's codes."""

    def __init__(self, code: str):
        url = f"{META_URL}?varcd={code}&lang=PT"
        m = _fetch_json(url, CACHE / f"ine_meta_{code}.json")[0]
        if m.get("IndicadorCod") != code:
            raise RuntimeError(f"{code}: metadata is for {m.get('IndicadorCod')}")
        self.code = code
        self.name = m["IndicadorNome"]
        self.first, self.last = m["PrimeiroPeriodo"], m["UltimoPeriodo"]
        self.cats: dict[str, dict[str, str]] = {}
        for blk in m["Dimensoes"]["Categoria_Dim"]:
            for cats in blk.values():
                for c in cats:
                    self.cats.setdefault(c["dim_num"], {})[c["categ_cod"]] = \
                        c["categ_dsg"]
        self.period_by_label = {v: k for k, v in self.cats["1"].items()}

    def has(self, dim: int, code: str) -> bool:
        return code in self.cats.get(str(dim), {})

    def periods(self, kind: str) -> list[str]:
        """Window period codes of one kind present in the metadata.

        kind: "A" annual (S7A), "Q" quarterly (S5A), "M" monthly (S3A),
        "S" three-year spans (S16A, attributed to their end year).
        """
        prefix = {"A": "S7A", "Q": "S5A", "M": "S3A", "S": "S16A"}[kind]
        out = []
        for p in self.cats["1"]:
            if not p.startswith(prefix):
                continue
            year = int(p[len(prefix):][-4:] if kind == "S"
                       else p[len(prefix):len(prefix) + 4])
            if Y0 - 1 <= year <= Y1:
                out.append(p)
        if not out:
            raise RuntimeError(f"{self.code}: no {kind} periods in window")
        return sorted(out)


def query(meta: Meta, periods: list[str], step: int = 60,
          **dims: str | list[str]) -> dict[tuple, float]:
    """{(period_code, dim2, dim3, …): value} for one indicator.

    dims are Dim2=…, Dim3=… as a code or a list of codes; every code is
    checked against the metadata first, so a typo fails here rather than
    as a Sucesso.Falso three calls in.
    """
    norm: dict[int, list[str]] = {}
    for k, v in dims.items():
        n = int(k.removeprefix("Dim"))
        codes = [v] if isinstance(v, str) else list(v)
        for c in codes:
            if not meta.has(n, c):
                raise AssertionError(f"{meta.code}: Dim{n}={c} not in metadata")
        norm[n] = codes
    width = math.prod(len(v) for v in norm.values())
    step = max(1, min(step, CELL_CAP // width))
    out: dict[tuple, float] = {}
    for i in range(0, len(periods), step):
        chunk = periods[i:i + step]
        assert len(chunk) * width <= CELL_CAP
        params = [("op", "2"), ("varcd", meta.code),
                  ("Dim1", ",".join(chunk))]
        params += [(f"Dim{n}", ",".join(norm[n])) for n in sorted(norm)]
        params.append(("lang", "PT"))
        qs = urllib.parse.urlencode(params, safe=",")
        tag = hashlib.sha1(qs.encode()).hexdigest()[:12]
        payload = _fetch_json(f"{DATA_URL}?{qs}",
                              CACHE / f"ine_data_{meta.code}_{tag}.json")
        dados = payload[0].get("Dados")
        if not isinstance(dados, dict):
            raise RuntimeError(f"{meta.code}: no Dados in a Sucesso payload")
        for label, rows in dados.items():
            if label not in meta.period_by_label:
                raise RuntimeError(f"{meta.code}: unknown period {label!r}")
            p = meta.period_by_label[label]
            for r in rows:
                v = r.get("valor")
                if v in (None, ""):
                    continue
                key = (p, r["geocod"]) + tuple(
                    r[f"dim_{n}"] for n in sorted(norm) if n >= 3)
                if key in out:
                    raise RuntimeError(f"{meta.code}: duplicate cell {key}")
                # `valor` is already in the indicator's unit (Potencia10
                # is a label: 0013428's "71197.965" is € millions).
                out[key] = float(v)
    return out


def year_of(p: str) -> int:
    if p.startswith("S16A"):
        return int(p[-4:])
    return int(p[3:7])


def annual(meta: Meta, *rest: str, **dims) -> dict[int, float]:
    """{year: value} for a single-cell-per-year annual query."""
    cells = query(meta, meta.periods("A"), **dims)
    out: dict[int, float] = {}
    for key, v in cells.items():
        if tuple(key[2:]) == rest or not rest:
            y = year_of(key[0])
            if y in out:
                raise RuntimeError(f"{meta.code}: two cells for {y}; "
                                   "pass the categories to pick")
            out[y] = v
    return out


def by_year_sum(cells: dict[tuple, float], select=lambda key: True
                ) -> dict[int, tuple[float, int]]:
    """{year: (sum, n_periods)} over sub-annual cells passing `select`."""
    acc: dict[int, list[float]] = {}
    for key, v in cells.items():
        if select(key):
            acc.setdefault(year_of(key[0]), []).append(v)
    return {y: (sum(vs), len(vs)) for y, vs in acc.items()}


# ------------------------------------------------------------------- checks

def check(label: str, got: float | None, want: float, tol: float = 0.0
          ) -> None:
    if got is None or abs(got - want) > tol + 1e-9:
        raise AssertionError(f"spot check {label}: got {got}, want {want}")
    print(f"  ok  {label} = {got:g}")


# ------------------------------------------------------------------- output

def write(rel: str, comments: list[str], header: str,
          columns: list[dict], fmts: list[str]) -> int:
    path = DATA / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {c}" if c else "#" for c in comments] + [header]
    n = 0
    for y in range(Y0, Y1 + 1):
        cells = []
        for col, fmt in zip(columns, fmts):
            v = col.get(y)
            cells.append("" if v is None else
                         (v if isinstance(v, str) else fmt.format(v)))
        if any(cells):
            lines.append(f"{y}," + ",".join(cells))
            n += 1
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  -> data/{rel} ({n} rows)")
    return n


def window(d: dict[int, float]) -> dict[int, float]:
    return {y: v for y, v in d.items() if Y0 <= y <= Y1}


# ------------------------------------------------------------------ series

def gdp() -> None:
    m = Meta("0013428")
    q = by_year_sum(query(m, m.periods("Q"), Dim2="PT"))
    nominal = {y: s for y, (s, n) in q.items() if n == 4}
    quarters = {y: n for y, (s, n) in q.items()}
    check("GDP 2024 (sum of 4 quarters, €mn)", round(nominal.get(2024, 0)),
          291_153)
    g = Meta("0014144")
    # The comment below calls this the regional-accounts vintage; if INE
    # repoints the code, or the regional release catches up with the
    # national accounts, the comment has to be rewritten, so fail here.
    assert "regionais" in g.name, f"0014144 is now {g.name!r}"
    growth = annual(g, Dim2="PT")
    if growth.get(2024) != 2.1 or 2025 in growth:
        raise AssertionError("0014144 moved (2024 = "
                             f"{growth.get(2024)}, 2025 present: "
                             f"{2025 in growth}) — re-check the vintage note")
    write("macro/gdp_from_ine.csv", [
        "INE Contas Nacionais Trimestrais 0013428: GDP at current prices,",
        "base 2021, EUR MILLIONS, the SUM of the four published quarterly",
        "levels (quarters are levels, not annualised rates). A year with",
        "fewer than four published quarters is left blank; its count is in",
        "quarters_published. real_growth_pct = 0014144, an ANNUAL volume",
        "rate (prices of the previous year) but from the REGIONAL accounts",
        "(Contas económicas regionais, NUTS-2024, last updated 2026-01-06;",
        "2024 flagged provisional): an OLDER VINTAGE than the nominal",
        "column. Its 2024 = 2.1 predates the September-2026 national",
        "accounts, on which 2024 is 2.7 (Eurostat nama_10_gdp; INE's own",
        "quarterly y/y 0013431 runs 2.4/2.6/2.7/3.0 through 2024). It is",
        "not a Q4 y/y and not a different base. 2006–2023 agree with",
        "Eurostat to the decimal; 2025 is not in it yet. Quarterly y/y",
        "(0013431) is not carried: it does not aggregate to a year.",
    ], "year,nominal_eurmn,quarters_published,real_growth_pct",
        [window(nominal), window(quarters), window(growth)],
        ["{:.1f}", "{:d}", "{:.1f}"])


def ipc() -> None:
    avg, yoy = Meta("0014649"), Meta("0014647")
    dec = [p for p in avg.periods("M") if p.endswith("12")]
    a = {year_of(k[0]): v for k, v in
         query(avg, dec, Dim2="PT", Dim3="T").items()}
    dec_y = [p for p in yoy.periods("M") if p.endswith("12")]
    b = {year_of(k[0]): v for k, v in
         query(yoy, dec_y, Dim2="PT", Dim3="T").items()}
    check("IPC avg rate Dec-2024", a.get(2024), 2.42)
    check("IPC avg rate Dec-2022", a.get(2022), 7.83)
    check("IPC avg rate Dec-2025", a.get(2025), 2.34)
    write("macro/ipc_from_ine.csv", [
        "INE IPC, base 2025 (linked series). ipc_avg_rate = the DECEMBER",
        "reading of 0014649 (rate of the 12-month average) — INE's official",
        "annual average inflation. ipc_yoy_december = December y/y from",
        "0014647. The running year has no December and is left blank.",
        "This is the national CPI, NOT the HICP (hicp_from_estat.csv).",
    ], "year,ipc_avg_rate,ipc_yoy_december",
        [window(a), window(b)], ["{:.2f}", "{:.2f}"])


def unemployment() -> None:
    s21 = annual(Meta("0012173"), Dim2="PT", Dim3="T")
    s11 = annual(Meta("0006191"), Dim2="PT", Dim3="T")
    check("unemployment Série 2021, 2024", s21.get(2024), 6.4)
    check("unemployment Série 2021, 2023", s21.get(2023), 6.5)
    check("unemployment Série 2021, 2025", s21.get(2025), 6.0)
    mm = Meta("0007976")
    monthly = by_year_sum(query(mm, mm.periods("M"), Dim2="PT", Dim3="T"))
    mean = {y: s / n for y, (s, n) in monthly.items() if n == 12}
    months = {y: n for y, (s, n) in monthly.items()}
    write("macro/unemployment_from_ine.csv", [
        "INE Inquérito ao Emprego — THREE vintages, never spliced:",
        "  rate_serie2021 = 0012173 (Série 2021, annual, 2011+);",
        "  rate_serie2011 = 0006191 (Série 2011, annual, 2011–2020);",
        "  rate_monthly_mean = mean of the twelve monthly estimates of",
        "  0007976 (16–74; each month is a centred 3-month window), blank",
        "  unless all twelve are published (count in monthly_months).",
        "The 2021 questionnaire change and census reweighting are a seam.",
    ], "year,rate_serie2021,rate_serie2011,rate_monthly_mean,monthly_months",
        [window(s21), window(s11), window(mean), window(months)],
        ["{:.1f}", "{:.1f}", "{:.2f}", "{:d}"])


def demography() -> None:
    pop = annual(Meta("0004167"), Dim2="PT", Dim3="T", Dim4="T")
    check("population 31-Dec-2024 (revised)", pop.get(2024), 11_387_222)
    b13 = annual(Meta("0008086"), Dim2="PT", Dim3="T", Dim4="T")
    check("births 2020 (NUTS-2013)", b13.get(2020), 84_530)
    check("births 2023 (NUTS-2013)", b13.get(2023), 85_699)
    b24 = annual(Meta("0012436"), Dim2="PT", Dim3="T", Dim4="T")
    bm = Meta("0012094")
    bmon = by_year_sum(query(bm, bm.periods("M"), Dim2="PT", Dim3="T"))
    bm_sum = {y: s for y, (s, n) in bmon.items()}
    bm_n = {y: n for y, (s, n) in bmon.items()}
    dm = Meta("0008834")
    dcells = query(dm, dm.periods("A"), Dim2="PT", Dim3="T",
                   Dim4=["APU", "AMU", "APR"])
    dsum = by_year_sum(dcells)
    deaths = {y: s for y, (s, n) in dsum.items() if n == 3}
    check("deaths 2020 (APU+AMU+APR)", deaths.get(2020), 123_385)
    check("deaths 2023 (APU+AMU+APR)", deaths.get(2023), 118_328)
    tfr = annual(Meta("0001293"), Dim2="PT")
    le = Meta("0001724")
    lcells = query(le, le.periods("S"), Dim2="PT", Dim3=["T", "1", "2"])
    life = {s: {year_of(k[0]): v for k, v in lcells.items() if k[2] == s}
            for s in ("T", "1", "2")}
    span = {year_of(p): le.cats["1"][p].replace(" ", "")
            for p in le.periods("S")}
    overlap = sorted(set(b13) & set(b24))
    for y in overlap:
        print(f"  ..  births {y}: NUTS-2013 {b13[y]:.0f} vs NUTS-2024 "
              f"{b24[y]:.0f}")
    write("social/demography_from_ine.csv", [
        "INE vital statistics and population, Portugal = RESIDENTS (geo",
        "code PT; the cubes' 'T' total also counts non-residents).",
        "population = 0004167, REVISED vintage, 31 DECEMBER of the year",
        "(INE 2024 = Eurostat demo_gind 1-Jan-2025 = 11,387,222).",
        *VINTAGE_MAP,
        "births_nuts2013 = 0008086 (2011–2023); births_nuts2024 = 0012436",
        "(annual); births_monthly_nuts2024 = sum of the published months of",
        "0012094 (count in births_monthly_months) — PARTIAL year, not a",
        "total. Separate columns, never spliced; overlap years measure the",
        "seam. deaths_nuts2013 = 0008834, APU+AMU+APR (no total category;",
        "2011–2023 only). tfr = 0001293. life_exp_* = 0001724, three-year",
        "tables attributed to their END year (span in life_exp_span).",
    ], "year,population,births_nuts2013,births_nuts2024,"
       "births_monthly_nuts2024,births_monthly_months,deaths_nuts2013,tfr,"
       "life_exp_span,life_exp_total,life_exp_men,life_exp_women",
        [window(pop), window(b13), window(b24), window(bm_sum),
         window(bm_n), window(deaths), window(tfr), window(span),
         window(life["T"]), window(life["1"]), window(life["2"])],
        ["{:.0f}", "{:.0f}", "{:.0f}", "{:.0f}", "{:d}", "{:.0f}",
         "{:.2f}", "{}", "{:.2f}", "{:.2f}", "{:.2f}"])


def causes_of_death() -> None:
    old, new = Meta("0008206"), Meta("0013166")
    causes = [c for c in old.cats["5"] if c != "T-LES"]
    assert causes == [c for c in new.cats["5"] if c != "T-LES"], \
        "the two cause lists differ; the seam is no longer one-to-one"
    assert old.cats["5"]["64"].startswith("Homicídios")
    # The cause cubes are vast (geo × sex × age × cause × year) and the
    # server's cost grows with the number of PERIODS asked, not cells:
    # ~45 s per year for all 65 causes, while 18 years in one call times
    # out. One call per year, each cached, so a rerun resumes.
    yrs = lambda m: [p for p in m.periods("A") if year_of(p) >= Y0]
    a = query(old, yrs(old), step=1, Dim2="PT", Dim3="T", Dim4="T",
              Dim5=causes)
    b = query(new, yrs(new), step=1, Dim2="PT", Dim3="T", Dim4="T",
              Dim5=causes)
    va = {(year_of(k[0]), k[4]): v for k, v in a.items()}
    vb = {(year_of(k[0]), k[4]): v for k, v in b.items()}
    check("assault deaths 2022 (0008206 code 64)", va.get((2022, "64")), 97)
    check("assault deaths 2021 (0008206 code 64)", va.get((2021, "64")), 93)
    check("assault deaths 2022 (0013166 code 64)", vb.get((2022, "64")), 97)
    lines = [
        "# INE Óbitos por causas de morte, European shortlist, Portugal",
        "# residents (geo PT, both sexes, all ages). deaths_nuts2013 =",
        "# 0008206 (1980–2022), deaths_nuts2024 = 0013166 (2022–2024); 2022",
        "# is on both and measures the seam — never splice. Code 64 =",
        "# assault (ICD-10 X85–Y09), the death-certificate homicide count.",
        "# All-causes (T-LES) is refused by the API: totals are in",
        "# demography_from_ine.csv (0008834).",
        "year,cause_code,cause,deaths_nuts2013,deaths_nuts2024",
    ]
    n = 0
    for y in range(Y0, Y1 + 1):
        for c in causes:
            x, z = va.get((y, c)), vb.get((y, c))
            if x is None and z is None:
                continue
            name = json.dumps(old.cats["5"][c], ensure_ascii=False)
            lines.append(f"{y},{c},{name},"
                         f"{'' if x is None else f'{x:.0f}'},"
                         f"{'' if z is None else f'{z:.0f}'}")
            n += 1
    path = DATA / "social" / "causes_of_death_from_ine.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  -> data/social/causes_of_death_from_ine.csv ({n} rows)")


CRIME_CATS = {"T": "total", "1": "physical_integrity",
              "2": "street_theft", "3": "vehicle_theft",
              "4": "drink_driving", "5": "unlicensed_driving",
              "6": "property"}


def crime() -> None:
    cols, names = [], []
    for code, tag in (("0008074", "nuts2013"), ("0012260", "nuts2024")):
        m = Meta(code)
        cells = query(m, m.periods("A"), Dim2="PT", Dim3=list(CRIME_CATS))
        for cat, label in CRIME_CATS.items():
            cols.append(window({year_of(k[0]): v for k, v in cells.items()
                                if k[2] == cat}))
            names.append(f"{label}_{tag}")
    check("crime rate total 2024 (0012260, ‰)", cols[7].get(2024), 31.2)
    write("social/crime_from_ine.csv", [
        "INE / DGPJ recorded-crime RATE per 1,000 inhabitants, Portugal, by",
        "category. *_nuts2013 = 0008074 (2011–2022), *_nuts2024 = 0012260",
        "(2021+); 2021–2022 are on both — never splice. NO homicide",
        "category: homicide is in Eurostat crim_off_cat and in",
        "causes_of_death_from_ine.csv (code 64). The rates' denominators",
        "follow each vintage's population estimates.",
    ], "year," + ",".join(names), cols, ["{:.1f}"] * len(cols))


def gini_poverty() -> None:
    g = annual(Meta("0004212"), Dim2="PT")
    write("social/gini_from_ine.csv", [
        "INE ICOR (national EU-SILC) 0004212: Gini of net monetary income",
        "per equivalent adult, %, Portugal. YEAR = the INCOME reference",
        "year, one behind the ICOR/EU-SILC survey year: INE 2024 = Eurostat",
        "ilc_di12 2025 (verified equal 2013–2024). 2003+; Eurostat ilc_di12",
        "PT covers only 2014+ — two files, never spliced; shift a year",
        "before comparing them.",
    ], "year,gini", [window(g)], ["{:.1f}"])
    p13 = annual(Meta("0009821"), Dim2="PT")
    p24 = annual(Meta("0014079"), Dim2="PT")
    write("social/poverty_from_ine.csv", [
        "INE ICOR at-risk-of-poverty rate after social transfers (60% of",
        "the median), %, Portugal. rate_nuts2013 = 0009821 (2017+),",
        "rate_nuts2024 = 0014079 (2023+). A relative threshold. YEAR = the",
        "INCOME reference year, as gini_from_ine.csv: INE 2024 = Eurostat",
        "ilc_li02 2025 (verified equal 2017–2024).",
    ], "year,rate_nuts2013,rate_nuts2024",
        [window(p13), window(p24)], ["{:.1f}", "{:.1f}"])


TRADE_PARTNERS = ["MUNDO", "INTRA_UE27_2020", "EXTRA_UE27_2020", "ES", "FR",
                  "DE", "IT", "NL", "GB", "XU", "XI", "US", "AO", "BR", "CN"]


def goods_trade() -> None:
    cols, names, months_col = [], [], None
    for code, flow in (("0004172", "exports"), ("0004169", "imports")):
        m = Meta(code)
        cells = query(m, m.periods("M"), Dim2=TRADE_PARTNERS, Dim3="T")
        # TRAP: the EU-27 (2020) aggregates were not compiled back to 2005
        # — those months carry intra = extra = 0 (a placeholder zero, not a
        # blank) beside a positive world total. They are dropped, so the
        # affected years come out blank rather than as zero intra-EU trade.
        dropped = 0
        for p in {k[0] for k in cells}:
            i = cells.get((p, "INTRA_UE27_2020", "T"))
            e = cells.get((p, "EXTRA_UE27_2020", "T"))
            if i == 0 and e == 0 and cells.get((p, "MUNDO", "T"), 0) > 0:
                del cells[(p, "INTRA_UE27_2020", "T")]
                del cells[(p, "EXTRA_UE27_2020", "T")]
                dropped += 1
        # Same trap after Brexit: from 2021 the UK is split into XU (Great
        # Britain) and XI (Northern Ireland) and GB carries a zero.
        gb0 = 0
        for p in {k[0] for k in cells}:
            if cells.get((p, "GB", "T")) == 0 and (
                    cells.get((p, "XU", "T"), 0)
                    + cells.get((p, "XI", "T"), 0)) > 0:
                del cells[(p, "GB", "T")]
                gb0 += 1
            elif cells.get((p, "GB", "T"), 0) > 0:
                for x in ("XU", "XI"):     # and the mirror zeros before
                    if cells.get((p, x, "T")) == 0:
                        del cells[(p, x, "T")]
        print(f"  ..  {code}: {dropped} months with placeholder-zero EU-27 "
              f"aggregates and {gb0} post-Brexit GB zeros dropped")
        # Consistency, not a typed number: the world total must be the
        # intra- plus the extra-EU27 flow, month by month.
        for p in {k[0] for k in cells}:
            w = cells.get((p, "MUNDO", "T"))
            i = cells.get((p, "INTRA_UE27_2020", "T"))
            e = cells.get((p, "EXTRA_UE27_2020", "T"))
            if None not in (w, i, e):
                assert abs(w - (i + e)) <= 2, \
                    f"{code} {p}: world {w} != intra {i} + extra {e}"
        world_n = {y: n for y, (v, n) in
                   by_year_sum(cells, lambda k: k[1] == "MUNDO").items()}
        for partner in TRADE_PARTNERS:
            s = by_year_sum(cells, lambda k, pp=partner: k[1] == pp)
            # a partner-year counts only when every month the world total
            # has is there too; otherwise blank, never a short sum
            cols.append(window({y: v for y, (v, n) in s.items()
                                if n == world_n.get(y)}))
            names.append(f"{flow}_{partner.lower()}_eur")
            if partner == "MUNDO":
                mc = window({y: n for y, (v, n) in s.items()})
                if months_col is None:
                    months_col = mc
                assert mc == months_col, "exports and imports months differ"
    print("  ok  goods trade: world = intra-EU27 + extra-EU27, every month")
    write("trade/goods_trade_from_ine.csv", [
        "INE Estatísticas do comércio internacional de bens, CPA-2008 total,",
        "EUR (units, not millions): exports 0004172 by destination, imports",
        "0004169 by origin, monthly summed to the year. months = months",
        "published; the running year is PARTIAL (compare like with like).",
        "mundo = world; intra/extra_ue27_2020 = EU-27 (2020 composition)",
        "applied to the whole run, NOT compiled for 2005–2012 (INE serves",
        "placeholder zeros there; left blank). Partners by ISO-2 code (ao =",
        "Angola, br = Brazil). UK: gb = whole UK through 2020; from 2021 INE",
        "splits it into xu (Great Britain) and xi (Northern Ireland) and gb",
        "is blank — a seam, not a collapse. Goods only — not the",
        "national-accounts P6/P7 (trade_from_estat.csv).",
    ], "year,months," + ",".join(names), [months_col] + cols,
        ["{:d}"] + ["{:.0f}"] * len(cols))


def migration() -> None:
    im = Meta("0006055")
    cells = query(im, im.periods("A"), Dim2="PT", Dim3="T", Dim4="T",
                  Dim5=["T", "PT", "EST", "99"])
    imm = {n: window({year_of(k[0]): v for k, v in cells.items()
                      if k[4] == n}) for n in ("T", "PT", "EST", "99")}
    for y, want in ((2019, 95_382), (2020, 83_654), (2021, 222_775),
                    (2022, 495_979), (2023, 461_751), (2024, 394_904),
                    (2025, 254_253)):
        check(f"immigrants {y}", imm["T"].get(y), want)
    write("migration/immigration_from_ine.csv", [
        "INE Estimativas anuais de imigração 0006055: permanent immigrants,",
        "Portugal, both sexes, all ages, by nationality (portuguese /",
        "foreign / unknown).",
        *VINTAGE_MAP,
        "2008–2020 census/survey-based; 2021+ administrative base.",
    ], "year,immigrants,portuguese,foreign,unknown_nationality",
        [imm["T"], imm["PT"], imm["EST"], imm["99"]], ["{:.0f}"] * 4)

    em = Meta("0006050")
    ecells = query(em, em.periods("A"), Dim2="PT", Dim3=["T", "1", "2"])
    emi = {s: window({year_of(k[0]): v for k, v in ecells.items()
                      if k[2] == s}) for s in ("T", "1", "2")}
    check("emigrants 2019", emi["T"].get(2019), 28_219)
    check("emigrants 2021", emi["T"].get(2021), 120_806)
    check("emigrants 2024", emi["T"].get(2024), 188_871)
    write("migration/emigration_from_ine.csv", [
        "INE Estimativas anuais de emigração 0006050: permanent emigrants,",
        "Portugal, total and by sex. The pre-2021 register-based figures",
        "undercount departures; the 2021+ revision is the correction.",
        *VINTAGE_MAP,
    ], "year,emigrants,men,women", [emi["T"], emi["1"], emi["2"]],
        ["{:.0f}"] * 3)

    n13 = annual(Meta("0008269"), Dim2="PT")
    n24 = annual(Meta("0013179"), Dim2="PT")
    for y in sorted(set(n13) & set(n24)):
        print(f"  ..  net migration {y}: NUTS-2013 {n13[y]:.0f} vs NUTS-2024 "
              f"{n24[y]:.0f}")
    write("migration/net_migration_from_ine.csv", [
        "INE saldo migratório (includes statistical adjustment), Portugal.",
        "net_nuts2013 = 0008269 (2011–2023), net_nuts2024 = 0013179 (2021+).",
        "Both carry the revised administrative base from 2021 (the overlap",
        "years 2021–2023 were identical at fetch time); the seam is 2020→2021",
        "methodology inside each column. Two indicators, never spliced.",
        *VINTAGE_MAP,
    ], "year,net_nuts2013,net_nuts2024", [window(n13), window(n24)],
        ["{:.0f}", "{:.0f}"])

    groups = ["T", "UE27_2020", "EXTRA_UE27_2020"]
    cols, names = [], []
    for code, tag in (("0009107", "nuts2013"), ("0013220", "nuts2024")):
        m = Meta(code)
        c = query(m, m.periods("A"), Dim2="PT", Dim3="T", Dim4=groups)
        for g in groups:
            cols.append(window({year_of(k[0]): v for k, v in c.items()
                                if k[3] == g}))
            names.append(f"{'total' if g == 'T' else g.lower()}_{tag}")
    nat = Meta("0010247")
    nats = list(nat.cats["3"])
    c = query(nat, nat.periods("A"), Dim2="PT", Dim3=nats)
    for n in nats:
        cols.append(window({year_of(k[0]): v for k, v in c.items()
                            if k[2] == n}))
        names.append(f"bynat_{n.lower()}")
    for y in sorted(set(cols[0]) & set(cols[len(groups) * 2])):
        assert cols[0][y] == cols[len(groups) * 2][y], \
            f"foreign residents {y}: 0009107 and 0010247 totals differ"
    print("  ok  foreign residents: 0009107 total = 0010247 total, all years")
    write("migration/foreign_residents_from_ine.csv", [
        "INE (source of record SEF/AIMA): foreign population with LEGAL",
        "RESIDENT STATUS — the permit-based stock, not the register/survey",
        "stock. *_nuts2013 = 0009107, *_nuts2024 = 0013220 (2021+), by",
        "group (total / EU-27 2020 / extra-EU-27 2020); bynat_* = 0010247",
        "(2014+), top-ten nationalities by ISO-2 code (top = all others).",
        "ALL STALE AT 2023: the SEF→AIMA transition broke the series.",
    ], "year," + ",".join(names), cols, ["{:.0f}"] * len(cols))


def main() -> None:
    print("Fetching INE Portugal series" + (" (live, --refresh)" if REFRESH
                                            else "") + "...")
    gdp()
    ipc()
    unemployment()
    demography()
    causes_of_death()
    crime()
    gini_poverty()
    goods_trade()
    migration()
    print("Done. Diff the *_from_ine.csv sidecars before adopting.")


if __name__ == "__main__":
    main()
