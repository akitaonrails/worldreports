#!/usr/bin/env python3
"""Chile's deaths, and the population DEIS divides them by, from MINSAL/DEIS.

Usage:  python3 -I countries/chile/fetch/fetch_deis.py

Writes two review sidecars:
  data/mortality/deaths_from_deis.csv  year, deaths, population,
                                       crude_death_rate_per_1000

Publisher: Ministerio de Salud, Departamento de Estadísticas e
Información de Salud (DEIS), published on the state open-data portal
datos.gob.cl as "Defunciones por Semana Epidemiológica, Sexo, Grupo de
Edad y Región" (resource DEF_SEMANA_EPIDEMIOLOGICA.csv, updated
2025-11-04).

What this series is and is not:
  * It is a count of registered deaths by epidemiological week of
    occurrence, aggregated over region, sex and five age bands. It is the
    vital-statistics count, not a cause-of-death table: it cannot say what
    anybody died of, and this fetcher does not pretend otherwise.
  * POBLACION is the population of each age-sex cell of each region, not
    the region total; the annual denominator is the sum over the cells,
    which reproduces INE's projected population to within rounding.
  * The current year is incomplete and its later weeks are present as
    zeros. A year is only published here once it has 52+ weeks AND its
    last weeks carry deaths, so a running year can never be drawn as a
    year's result.
"""
from __future__ import annotations

import csv
import io
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache" / "deis"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)", "Accept": "*/*"}

URL = ("https://datos.gob.cl/dataset/1c2811cd-13a4-4406-b20d-cda1544b65d0/"
       "resource/90d092cc-bf19-4bcc-bfb0-22b0c5db6707/download/"
       "def_semana_epidemiologica.csv")

FIRST_YEAR, LAST_YEAR = 2005, 2026
# One known annual total per era, read off the publisher 2026-10-25: the
# last pre-pandemic year, the second pandemic year, and a recent one.
SPOT = {2019: 109_324, 2021: 137_267, 2024: 126_322}


class FetchError(RuntimeError):
    pass


def get(url: str, cache_name: str, check) -> bytes:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / cache_name
    if path.exists():
        raw = path.read_bytes()
        try:
            check(raw)
            return raw
        except Exception as e:  # noqa: BLE001
            print(f"  stale cache {cache_name}: {e}", file=sys.stderr)
            path.unlink()
    last: Exception | None = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=300) as r:
                raw = r.read()
            check(raw)
            path.write_bytes(raw)
            return raw
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"  {cache_name} attempt {attempt + 1}: {e}", file=sys.stderr)
            time.sleep(3 * (attempt + 1))
    raise FetchError(f"{url}: {last}")


def main() -> int:
    def check(raw: bytes) -> None:
        text = raw.decode("utf-8-sig", "replace")
        if not text.startswith("ANO_ESTADISTICO|SEMANA_ESTADISTICA|"):
            raise ValueError(f"not the DEIS weekly deaths file: {text[:80]!r}")
        if "<html" in text[:200].lower():
            raise ValueError("HTML served where the CSV should be")

    raw = get(URL, "def_semana_epidemiologica.csv", check)
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig")),
                               delimiter="|"))
    if len(rows) < 100_000:
        raise FetchError(f"only {len(rows)} rows: truncated payload?")

    deaths: dict[int, int] = defaultdict(int)
    weeks: dict[int, set[int]] = defaultdict(set)
    pop_cells: dict[tuple[int, str, str, str], int] = {}
    regions = set()
    for r in rows:
        year = int(r["ANO_ESTADISTICO"])
        if not FIRST_YEAR <= year <= LAST_YEAR:
            continue
        regions.add(r["REGION"])
        deaths[year] += int(r["MUERTES_OBS"])
        weeks[year].add(int(r["SEMANA_ESTADISTICA"]))
        key = (year, r["REGION"], r["GRUPO_EDAD"], r["SEXO"])
        pop_cells[key] = max(pop_cells.get(key, 0), int(r["POBLACION"]))

    if len(regions) != 16:
        raise FetchError(f"{len(regions)} regions: Chile has 16")

    population: dict[int, int] = defaultdict(int)
    for (year, _region, _age, _sex), value in pop_cells.items():
        population[year] += value

    # A year counts as complete when it has at least 52 weeks and its final
    # weeks carry deaths. The running year fails that and is dropped.
    complete = {y for y in deaths
                if len(weeks[y]) >= 52 and _last_week_has_deaths(rows, y)}
    if LAST_YEAR in complete:
        complete.discard(LAST_YEAR)
    if not complete:
        raise FetchError("no complete year in the payload")

    for year, expected in SPOT.items():
        if year not in complete:
            raise FetchError(f"{year} is no longer a complete year")
        if deaths[year] != expected:
            raise FetchError(f"{year} deaths = {deaths[year]}, pinned {expected}")
    if not 18_000_000 <= population[max(complete)] <= 21_000_000:
        raise FetchError(f"population {population[max(complete)]} is not Chile")

    out = DATA / "mortality" / "deaths_from_deis.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["year", "deaths", "population",
                    "crude_death_rate_per_1000"])
        for year in sorted(complete):
            rate = deaths[year] / population[year] * 1000
            w.writerow([year, deaths[year], population[year], f"{rate:.2f}"])

    print(f"  DEIS deaths: {len(complete)} complete years "
          f"{min(complete)}-{max(complete)}, {len(rows)} rows")
    print(f"  latest complete year {max(complete)}: {deaths[max(complete)]} "
          f"deaths over {population[max(complete)]} people")
    print("  -> mortality/deaths_from_deis.csv")
    return 0


def _last_week_has_deaths(rows, year: int) -> bool:
    """True when the year's highest week number carries a non-zero count."""
    last = 0
    seen = 0
    for r in rows:
        if int(r["ANO_ESTADISTICO"]) != year:
            continue
        week = int(r["SEMANA_ESTADISTICA"])
        if week > last:
            last = week
        if week >= 50:
            seen += int(r["MUERTES_OBS"])
    return last >= 52 and seen > 0


if __name__ == "__main__":
    sys.exit(main())
