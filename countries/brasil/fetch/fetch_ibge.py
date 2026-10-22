#!/usr/bin/env python3
"""Fetch official annual series from IBGE SIDRA (v3 API).

  GDP (annual):     table 6784 — var 9808 nominal R$ mn, 9810 volume growth,
                    9812 per-capita R$, 93 population (Contas Nacionais Anuais)
  GDP (quarterly):  table 1846 — var 585, categories 90707 (PIB market prices)
                    and 93406 (FBCF), used to extend 2024-2026
  Growth (recent):  table 5932 — var 6563 (accumulated-in-year, Q4 = annual)
  Unemployment:     table 4099 — PNAD Contínua, annual avg of 4 quarters

Outputs: data/macro/gdp.csv, data/macro/unemployment.csv (best effort).
Raw JSON cached under cache/.
"""
import json
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"
DATA = ROOT / "data"
CACHE.mkdir(exist_ok=True)
API = "https://servicodados.ibge.gov.br/api/v3/agregados"


def get(url: str, cache_name: str) -> dict | list:
    cf = CACHE / cache_name
    if cf.exists():
        return json.loads(cf.read_text())
    last = None
    for attempt in range(5):
        try:
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            data = r.json()
            cf.write_text(json.dumps(data))
            return data
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"  {cache_name} attempt {attempt + 1}: {e}", file=sys.stderr)
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"failed {cache_name}: {last}")


def sidra_var(ag: str, periodos: str, var: str, classif: str | None = None,
              cache: str = "") -> dict[int, float]:
    url = f"{API}/{ag}/periodos/{periodos}/variaveis/{var}?localidades=BR"
    if classif:
        url += f"&classificacao={classif}"
    data = get(url, cache or f"sidra_{ag}_{var}_{abs(hash(url)) % 10**8}.json")
    out: dict[int, float] = {}
    for bloco in data:
        for res in bloco.get("resultados", []):
            for s in res.get("series", []):
                for periodo, valor in s["serie"].items():
                    if valor not in ("...", "-", None, ""):
                        out[int(periodo)] = float(valor)
    return out


def main() -> None:
    print("IBGE/SIDRA: annual GDP (6784)...")
    nominal = sidra_var("6784", "2006-2023", "9808", cache="sidra_6784_9808.json")
    growth = sidra_var("6784", "2006-2023", "9810", cache="sidra_6784_9810.json")
    percap = sidra_var("6784", "2006-2023", "9812", cache="sidra_6784_9812.json")
    pop = sidra_var("6784", "2006-2023", "93", cache="sidra_6784_93.json")

    print("IBGE/SIDRA: quarterly nominal GDP + FBCF (1846)...")
    q = sidra_var("1846", "200601-202602", "585",
                  classif="11255[90707,93406]", cache="sidra_1846_585.json")

    print("IBGE/SIDRA: quarterly growth accumulated (5932)...")
    g4 = sidra_var("5932", "200601-202604", "6563",
                   classif="11255[90707]", cache="sidra_5932_6563.json")

    # annual nominal from quarterly sums (extend to 2025; 2026 = H1 partial)
    q_nominal: dict[int, float] = {}
    for periodo, valor in q.items():
        year = periodo // 100
        q_nominal[year] = q_nominal.get(year, 0.0) + valor
    # but q holds PIB (90707) and FBCF (93406) mixed? categories come as
    # separate results; sidra_var flattens. Redo properly:
    url = (f"{API}/1846/periodos/200601-202602/variaveis/585"
           "?localidades=BR&classificacao=11255[90707,93406]")
    data = get(url, "sidra_1846_585_split.json")
    pib_q: dict[int, float] = {}
    fbcf_q: dict[int, float] = {}
    for bloco in data:
        for res in bloco.get("resultados", []):
            cats = res.get("classificacoes", [])
            if not cats:
                continue
            cat_id = next(iter(cats[0]["categoria"].keys()))
            target = pib_q if cat_id == "90707" else fbcf_q
            for s in res.get("series", []):
                for periodo, valor in s["serie"].items():
                    if valor not in ("...", "-", None, ""):
                        y = int(periodo) // 100
                        target[y] = target.get(y, 0.0) + float(valor)
    q_pib_annual = {y: v / 1000 for y, v in pib_q.items() if pib_q[y] != 0}
    q_fbcf_annual = {y: v / 1000 for y, v in fbcf_q.items() if fbcf_q[y] != 0}

    # unemployment: 4099, var 4099? discover variable id from metadata
    meta = get(f"{API}/4099/metadados", "sidra_4099_meta.json")
    var_desoc = next(v["id"] for v in meta["variaveis"]
                     if "desocupação" in v["nome"].lower())
    u = sidra_var("4099", "201201-202602", var_desoc,
                  classif=None, cache=f"sidra_4099_{var_desoc}.json")
    # annual average of quarterly rates; keep count of quarters seen
    u_sum: dict[int, tuple[float, int]] = {}
    for periodo, valor in u.items():
        y = periodo // 100
        s_, n_ = u_sum.get(y, (0.0, 0))
        u_sum[y] = (s_ + valor, n_ + 1)
    u_avg = {y: s_ / n_ for y, (s_, n_) in u_sum.items() if n_ == 4}
    u_partial = {y: s_ / n_ for y, (s_, n_) in u_sum.items() if 0 < n_ < 4}

    # Contas Nacionais only carries population through 2023, which left
    # per-capita blank for years that do have a GDP figure. Fill the tail from
    # IBGE's Projeções 2024 (data/social/population.csv, written by
    # fetch_ibge_population.py). The two agree to rounding over 2006-2023
    # (max 0.049M), so the splice does not introduce a step.
    pop_csv = DATA / "social" / "population.csv"
    if pop_csv.exists():
        added = []
        for line in pop_csv.read_text().splitlines()[1:]:
            year_s, pop_mn = line.split(",")[:2]
            y = int(year_s)
            if y not in pop and pop_mn:
                pop[y] = float(pop_mn) * 1000.0   # mn -> thousands
                added.append(y)
        if added:
            print(f"  population: filled {min(added)}-{max(added)} from "
                  "Projeções 2024")

    # ---- GDP per capita in USD = (nominal GDP / population) / avg USD -------
    avg_usd: dict[int, float] = {}
    dollar_csv = DATA / "macro" / "dollar.csv"
    if dollar_csv.exists():
        for line in dollar_csv.read_text().splitlines()[1:]:
            parts = line.split(",")
            if parts[1]:
                avg_usd[int(parts[0])] = float(parts[1])

    lines = ["year,nominal_rbi,real_growth,gdp_per_capita_usd,population_mn"]
    for y in range(2006, 2027):
        # canonical nominal GDP in R$ billion
        nom_bi = None
        if y <= 2023 and y in nominal:
            nom_bi = nominal[y] / 1000.0        # 6784 values are R$ million
        if y in (2024, 2025) and y in q_pib_annual:
            nom_bi = q_pib_annual[y]             # quarterly sums, already R$ bi
        grow = growth.get(y)
        if grow is None:
            grow = g4.get(y * 100 + 4)           # 5932 Q4 accumulated-in-year
        pc_usd = None
        if nom_bi and y in pop and y in avg_usd:
            pc_brl = nom_bi / (pop[y] / 1000.0) * 1000.0   # pop in thousands -> mn
            pc_usd = pc_brl / avg_usd[y]
        lines.append(",".join([
            str(y),
            f"{nom_bi:.1f}" if nom_bi else "",
            f"{grow:.1f}" if grow is not None else "",
            f"{pc_usd:.0f}" if pc_usd else "",
            f"{pop[y] / 1000.0:.1f}" if y in pop else "",
        ]))
    (DATA / "macro" / "gdp.csv").write_text("\n".join(lines) + "\n")
    print("  -> data/macro/gdp.csv")

    # quarterly-derived FBCF as cross-check output (does not overwrite curated)
    if q_fbcf_annual:
        lines = ["year,fbcf_rbi_from_quarters"]
        for y in sorted(q_fbcf_annual):
            lines.append(f"{y},{q_fbcf_annual[y]:.1f}")
        (DATA / "fiscal" / "fbcf_quarters_check.csv").write_text(
            "\n".join(lines) + "\n")
        print("  -> data/fiscal/fbcf_quarters_check.csv (check vs curated)")

    # unemployment
    lines = ["year,value"]
    for y in range(2012, 2027):
        v = u_avg.get(y, u_partial.get(y))
        lines.append(f"{y},{v:.1f}" if v else f"{y},")
    (DATA / "macro" / "unemployment_from_api.csv").write_text("\n".join(lines) + "\n")
    print("  -> data/macro/unemployment_from_api.csv (check vs curated)")

    print("partial quarters (unemployment):", u_partial)
    print("Done.")


if __name__ == "__main__":
    main()
