#!/usr/bin/env python3
"""Refresh Paraguay's INE series into sidecar CSVs.

Usage:  make C=paraguay fetch   (or: python3 -I fetch/fetch_ine.py)

The Instituto Nacional de Estadística publishes no machine API. Its
series are XLSX workbooks linked from the publication pages, and those
are what this fetcher reads. Every response is checked to be a real
workbook (XLSX is a ZIP, so the first two bytes are `PK`) before it is
cached: the INE's server answers an HTML error page under HTTP 200 for
a wrong path, and a cached error page is worse than no cache.

  Estimaciones y Proyecciones Nacional por año 1950-2050. Revisión 2024
      one workbook carrying the whole demography chapter: mid-year
      population, births, deaths, total fertility, crude birth and death
      rates, life expectancy, natural increase and net migration, by
      year, 1950-2050, one vintage. The 2022 census is inside it, so
      this series sits ~9% below the UN WPP series the World Bank
      republishes (2025: 6.42m here, 7.01m there). Two denominators,
      never spliced.

  EPHC labour-market rates (assets/documento/328/1. Tasas.xlsx)
      quarterly, 2017-2026, from the Encuesta Permanente de Hogares
      Continua. The annual figure staged here is the mean of the four
      quarters and exists only for years with all four.

  EPHC poverty incidence (the 1997/98-2021 long series, the 2022-2025
      departmental release, and the 2024-2025 national release used to
      check the departmental sum)

The EPHC Gini is not staged: INE publishes it only as a legacy .xls
(assets/documento/27/Ingresos_Indicadores de desigualdad...xls), and
reading BIFF needs `xlrd`, which requirements-fetch.txt does not carry.
The World Bank's SI.POV.GINI — the same survey harmonised — is the
staged Gini; SOURCES.yaml records the reason the national file is
missing rather than substituting a hand-copied number.

The pre-2017 Encuesta Permanente de Hogares and the 2017+ EPHC are
different survey designs; the poverty series carries that break and the
fetcher does not smooth it.
"""
from __future__ import annotations

import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"

BASE = "https://www.ine.gov.py"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}

YEAR_FROM, YEAR_TO = 2006, 2050

SOURCES = {
    "projections": (
        "/Publicaciones/Biblioteca/documento/266/"
        "Estimaciones y Proyecciones Nacional por año 1950-2050. "
        "Revisión 2024.xlsx"),
    "labour": "/assets/documento/328/1. Tasas.xlsx",
    "poverty_long": (
        "/assets/documento/11/Factor Revision 2025_Incidencia absoluta "
        "de pobreza extrema, pobreza no extrema, pobre y no pobre_py_EPH "
        "1997-98_2021.xlsx"),
    "poverty_recent": (
        "/assets/documento/11/Pobreza_incidencia absoluta y relativa, "
        "según área_py_EPHC 2024_2025.xlsx"),
    "poverty_dpto": (
        "/assets/documento/29/Pobreza_Incidencia de pobreza extrema, "
        "pobreza no extrema, pobre y no pobre (absoluto y relativo), "
        "segun dpto y anho EPHC 2022-2025.xlsx"),
}

COMMENTS = {
    "demography/population_from_ine.csv": [
        "INE Paraguay, Estimaciones y Proyecciones Nacional por año",
        "1950-2050, Revisión 2024 (one vintage, the 2022 census inside).",
        "Mid-year population; births and deaths are the projection's own",
        "estimates (2020-2022 carry the pandemic), not registered counts.",
        "Net migration is in THOUSANDS OF PERSONS ('En miles') in the",
        "source and is staged as such; the rate beside it is per 1,000.",
        "This denominator is ~9% below the UN WPP series the World Bank",
        "republishes (2025: 6,417,076 here, 7,013,000 there).",
    ],
    "macro/unemployment_from_ine.csv": [
        "INE EPHC, quarterly rates averaged to the year: total country,",
        "both sexes. Complete years only (2017-2025); a partial year is",
        "left blank rather than drawn as the year's rate. The survey",
        "design changed in 2017 (EPH -> EPHC).",
    ],
    "people/poverty_from_ine.csv": [
        "INE EPHC national poverty incidence, % of people, total country.",
        "Two survey regimes: EPH 1997/98-2016 and EPHC 2017-2025; the",
        "break is at 2017 and is not smoothed. Two-year surveys (1997/98,",
        "2000/01) are not staged because they have no single year.",
        "The 2022-2025 values are from the revised-weight (revision 2025)",
        "release.",
    ],
}


def fetch(key: str) -> Path:
    """Download one workbook into cache/, validating it is a workbook."""
    CACHE.mkdir(exist_ok=True)
    name = f"ine_{key}.xlsx"
    path = CACHE / name
    if path.exists():
        return path
    url = BASE + urllib.parse.quote(SOURCES[key], safe="/")
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=180) as r:
                raw = r.read()
            if not raw.startswith(b"PK") and not raw.startswith(b"\xd0\xcf"):
                raise ValueError("not a workbook (HTML served under 200?)")
            path.write_bytes(raw)
            return path
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"  {key} attempt {attempt + 1}: {e}", file=sys.stderr)
            time.sleep(3 * (attempt + 1))
    raise SystemExit(f"cannot fetch {url}: {last}")


def norm(text) -> str:
    """Accent- and case-insensitive label matching for the Spanish rows."""
    if text is None:
        return ""
    s = unicodedata.normalize("NFKD", str(text))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.lower().split())


def row_by_label(ws, needle: str, start: int = 1):
    for i, row in enumerate(
            ws.iter_rows(min_row=start, values_only=True), start):
        if needle in norm(row[1] if len(row) > 1 else None):
            return i, row
    raise SystemExit(f"label not found: {needle!r}")


def year_row(ws, row: int) -> list:
    return [c for c in next(ws.iter_rows(min_row=row, max_row=row,
                                         values_only=True))]


def series_by_year(ws, year_header_row: int, data_row: int) -> dict:
    years = year_row(ws, year_header_row)
    values = year_row(ws, data_row)
    out = {}
    for y, v in zip(years, values):
        if isinstance(y, (int, float)) and 1900 < y < 2200 and v is not None:
            out[int(y)] = float(v)
    return out


def write(rel: str, columns: list[tuple[str, dict, int]]) -> None:
    empty = [c for c, s, _ in columns if not s]
    if empty:
        raise SystemExit(f"{rel}: {empty} came back empty, nothing written")
    path = ROOT / "data" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {c}" for c in COMMENTS.get(rel, [])]
    lines.append("year," + ",".join(c for c, _, _ in columns))
    years = sorted(set().union(*(s for _, s, _ in columns)))
    rows = 0
    for y in years:
        if not YEAR_FROM <= y <= YEAR_TO:
            continue
        cells = [f"{series[y]:.{dec}f}" if y in series else ""
                 for _, series, dec in columns]
        lines.append(f"{y}," + ",".join(cells))
        rows += 1
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  data/{rel}  {rows} rows")


def demography() -> None:
    import openpyxl

    wb = openpyxl.load_workbook(fetch("projections"), data_only=True)
    comp = wb["Componentes Demográficos"]
    meas = wb["Medidas de Composición"]

    # Both sheets put the year series in row 7, columns C onward (A and B
    # are indent columns). Data rows are addressed by their Spanish label,
    # never by position: the workbook has blank spacer rows between
    # groups and re-ordering them would silently shift a column.
    labels = {
        "population": (meas, "ambos sexos"),
        "births": (comp, "nacimientos anuales"),
        "birth_rate_per_1000": (comp, "tasa bruta de natalidad"),
        "fertility_rate": (comp, "tasa global de fecundidad"),
        "deaths": (comp, "muertes anuales"),
        "death_rate_per_1000": (comp, "tasa bruta de mortalidad"),
        "life_expectancy": (comp, "total pais (ambos sexo)"),
        "natural_increase": (comp, "crecimiento anual (b-d)"),
        "natural_increase_rate_per_1000": (
            comp, "tasa de crecimiento natural"),
        "net_migration_thousands": (comp, "migracion anual: m"),
        "net_migration_rate_per_1000": (comp, "tasa de migracion m"),
    }
    series: dict[str, dict[int, float]] = {}
    for key, (ws, needle) in labels.items():
        i, _ = row_by_label(ws, needle)
        series[key] = series_by_year(ws, 7, i)

    # Known-value pins: the 1950 opening value is in the workbook's own
    # table 1 and the 2022 census-anchored year is the vintage marker.
    assert series["population"][1950] == 1517601, series["population"][1950]
    assert abs(series["population"][2022] - 6_284_020) < 1, \
        series["population"].get(2022)
    assert abs(series["fertility_rate"][2006] - 2.839) < 0.001
    assert abs(series["net_migration_rate_per_1000"][2006] - -8.49) < 0.01

    write("demography/population_from_ine.csv", [
        ("population", series["population"], 0),
        ("births", series["births"], 0),
        ("deaths", series["deaths"], 0),
        ("fertility_rate", series["fertility_rate"], 3),
        ("birth_rate_per_1000", series["birth_rate_per_1000"], 3),
        ("death_rate_per_1000", series["death_rate_per_1000"], 3),
        ("life_expectancy", series["life_expectancy"], 2),
        ("natural_increase", series["natural_increase"], 0),
        ("natural_increase_rate_per_1000",
         series["natural_increase_rate_per_1000"], 3),
        ("net_migration_thousands", series["net_migration_thousands"], 3),
        ("net_migration_rate_per_1000",
         series["net_migration_rate_per_1000"], 3),
    ])


def labour() -> None:
    import openpyxl

    wb = openpyxl.load_workbook(fetch("labour"), data_only=True)
    ws = wb.worksheets[0]
    # Columns C onward are four quarters per year from 2017; row 3 names
    # the year at the first quarter of each block.
    years = {c: int(v.split()[-1]) for c, v in enumerate(year_row(ws, 3))
             if isinstance(v, str) and v.startswith("Año")}
    quart = {}
    for label, column in (("tasa de desocupados", "unemployment_rate_pct"),
                          ("tasa de la fuerza de trabajo",
                           "participation_rate_pct"),
                          ("tasa de ocupados", "employment_rate_pct")):
        i, row = row_by_label(ws, label, start=5)
        # The first match under "Total país" is the both-sexes rate; the
        # same label repeats for Hombres and Mujeres further down.
        per_year: dict[int, list[float]] = {}
        for c in sorted(years):
            block = [row[c + k] if c + k < len(row) else None
                     for k in range(4)]
            if all(isinstance(v, (int, float)) for v in block):
                per_year[years[c]] = [float(v) for v in block]
        quart[column] = {y: sum(v) / 4.0 for y, v in per_year.items()}
    assert abs(quart["unemployment_rate_pct"][2019] - 6.1) < 0.5, \
        quart["unemployment_rate_pct"].get(2019)
    global YEAR_TO
    YEAR_TO = 2025  # a partial 2026 must not be drawn as the year's rate
    write("macro/unemployment_from_ine.csv",
          [(c, s, 2) for c, s in quart.items()])
    YEAR_TO = 2050


def poverty() -> None:
    import openpyxl

    out: dict[int, dict[str, float]] = {}

    # 1997/98-2021: counts by area; the rate is the published count of
    # poor over the published total, which is the same ratio INE prints.
    ws = openpyxl.load_workbook(fetch("poverty_long"),
                                data_only=True).worksheets[0]
    area = None
    for row in ws.iter_rows(min_row=4, values_only=True):
        label = norm(row[1] if len(row) > 1 else None)
        if label.startswith("total pais"):
            area = "total"
            continue
        if label.startswith("area urbana"):
            area = "urban"
            continue
        if label.startswith("area rural"):
            area = "rural"
            continue
        if area != "total" or len(row) < 7:
            continue
        y = row[1]
        if isinstance(y, (int, float)) and 1990 < y < 2030:
            poor, total = row[4], row[6]
            if poor and total:
                out.setdefault(int(y), {})["poverty_rate_pct"] = \
                    100.0 * poor / total
                out[int(y)]["extreme_poverty_rate_pct"] = \
                    100.0 * row[2] / total

    # 2022-2025: the departmental release carries every department but no
    # national row. The 15 departments plus Asuncion sum EXACTLY to the
    # published national absolute counts (asserted below against the
    # 2024-2025 national release), because both definitions exclude
    # Boqueron, Alto Paraguay, indigenous communities and collective
    # dwellings. So the sum is the national table, not a proxy for it.
    ws = openpyxl.load_workbook(fetch("poverty_dpto"),
                                data_only=True).worksheets[0]
    sums: dict[int, list[float]] = {}
    for row in ws.iter_rows(min_row=5, values_only=True):
        y = row[1]
        if not isinstance(y, (int, float)) or not 2020 < y < 2030:
            continue
        acc = sums.setdefault(int(y), [0.0, 0.0, 0.0])
        acc[0] += row[2] or 0.0
        acc[1] += row[6] or 0.0
        acc[2] += row[10] or 0.0
    for y, (extreme, poor, total) in sums.items():
        out.setdefault(y, {})["poverty_rate_pct"] = 100.0 * poor / total
        out[y]["extreme_poverty_rate_pct"] = 100.0 * extreme / total

    # Pin the sum against the published national release (2024-2025).
    ws = openpyxl.load_workbook(fetch("poverty_recent"),
                                data_only=True).worksheets[0]
    published = {}
    for row in ws.iter_rows(min_row=4, values_only=True):
        y = row[1]
        if (isinstance(y, (int, float)) and 2020 < y < 2030
                and row[4] is not None and row[6] is not None):
            published[int(y)] = (float(row[4]), float(row[6]))
    for y, (rate, extreme) in published.items():
        assert abs(out[y]["poverty_rate_pct"] - rate) < 0.01, \
            f"{y}: summed departments {out[y]['poverty_rate_pct']:.3f} " \
            f"vs published {rate:.3f}"
        assert abs(out[y]["extreme_poverty_rate_pct"] - extreme) < 0.01, \
            f"{y}: extreme poverty disagrees with the national release"

    assert abs(out[2006]["poverty_rate_pct"] - 47.27) < 0.5, \
        out[2006]["poverty_rate_pct"]
    assert abs(out[2025]["poverty_rate_pct"] - 16.0) < 0.6, \
        out[2025]["poverty_rate_pct"]
    cols = [("poverty_rate_pct",
             {y: v["poverty_rate_pct"] for y, v in out.items()
              if "poverty_rate_pct" in v}, 2),
            ("extreme_poverty_rate_pct",
             {y: v["extreme_poverty_rate_pct"] for y, v in out.items()
              if "extreme_poverty_rate_pct" in v}, 2)]
    # 1997/98 and 2000/01 are two-year surveys: no single year to key on.
    global YEAR_FROM
    YEAR_FROM = 2002
    write("people/poverty_from_ine.csv", cols)
    YEAR_FROM = 2006



def main() -> None:
    print("INE Paraguay")
    demography()
    labour()
    poverty()
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
