#!/usr/bin/env python3
"""Refresh the Eurostat-backed series for the United Kingdom into sidecar CSVs.

Usage:  python3 -I countries/united-kingdom/fetch/fetch_eurostat.py

The UK left the EU, so Eurostat is a RESIDUAL layer here, not the system of
record. Per-dataset state verified live against the API (2026-10-22):

  * DROPPED entirely (well-formed EMPTY cube under HTTP 200, not a 404):
    nama_10_gdp, gov_10dd_edpt1, une_rt_a, ilc_di12. This fetcher queries
    none of them; any query that comes back empty fails loudly, because with
    this API an empty result is how a dropped dataset or a bad filter
    presents.
  * FROZEN at 2019 (the pre-Brexit harmonised segment, ended by design —
    never extended, interpolated or spliced): prc_hicp_aind, migr_imm1ctz,
    migr_emi1ctz, migr_pop1ctz, migr_pop3ctb, migr_asyappctza, migr_acq.
    migr_imm3ctb starts 2008. migr_resfirst stops a year earlier (2018).
    The fetcher asserts the last populated year so a silently revived
    series is a loud failure, not a quiet change.
  * STILL CURRENT: demo_gind (population on 1 January to 2026) — the only
    Eurostat family here that still tracks the UK.

UK endpoint traps, all verified live:
  * unit=PER must NOT be added to the UK migration queries. Spain needed it
    for migr_asyappctza/migr_resfirst; on the UK slices it collapses the
    unit dimension to size 0 under HTTP 200 and the cube comes back
    well-formed and EMPTY. Unpinned, unit is size 1 for every UK slice.
  * migr_resfirst has NO sex dimension: pinning sex=T is a 400
    INVALID_QUERY_DIMENSION. It is omitted for that dataset only.
  * The EU27_2020_FOR / NEU27_2020_FOR citizenship cuts are EMPTY for the
    UK (the post-Brexit aggregate was never back-filled for a former
    member). The contemporaneous split is EU28_FOR / NEU28_FOR, populated
    only from 2013 (flows) or 2014 (stocks) — the blanks before that are
    real absences, carried as blanks.
  * migr_imm1ctz has a genuine hole at 2005, and migr_pop1ctz holes at
    2000 and 2002: carried blank, never interpolated (asserted).

Pinned values asserted on every run (from DISCOVERY.md, verified live):
2019 immigration 680,906 · 2019 emigration 368,385 · 2019 foreign-stock
frame total 66,647,112 · 2019 asylum 44,315 first-time / 46,130 total ·
2018 first permits 450,775 · 2019 naturalisations 159,348 · 2026
population on 1 January 69,554,275.

The Eurostat JSON-stat client is inlined from the shared Spain/France
helper (same decode logic, kept here so the country directory is
self-contained). Output goes to `*_from_estat.csv` sidecars only.
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

GEO = "UK"

# For a former member the EU27_2020 aggregates are empty; EU28 is the
# contemporaneous split for the whole 1998-2019 segment.
CUTS = {"total": "TOTAL", "national": "NAT",
        "eu28": "EU28_FOR", "non_eu28": "NEU28_FOR"}


def strides(size: list[int]) -> list[int]:
    """Row-major strides: JSON-stat numbers cells with the LAST dimension
    varying fastest, so the stride of dimension i is the product of every
    size after it."""
    out = [1] * len(size)
    for i in range(len(size) - 2, -1, -1):
        out[i] = out[i + 1] * size[i + 1]
    return out


def decode(payload: dict) -> dict[tuple[str, ...], float]:
    """{(code, code, ..., time): value} for every populated cell."""
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
            # Eurostat answers bursts with a 307 to sorry.ec.europa.eu
            # ("Server temporarily unavailable") — space the requests and
            # back off long enough for the wall to lift.
            time.sleep(2)
            with urllib.request.urlopen(url, timeout=120) as r:
                payload = json.loads(r.read())
            if "value" not in payload:
                raise ValueError("no value map in response")
            cache_file.write_text(json.dumps(payload))
            return payload
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"eurostat {dataset} {filters}: {last}")


def annual(dataset: str, cache_key: str | None = None,
           **filters) -> dict[int, float]:
    """A single annual series as {year: value}.

    Every dimension except `time` must be pinned by a filter or come back
    with size 1; a cube carrying several series is rejected rather than
    silently returning one of them.
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


def series(dataset: str, **filters) -> dict[int, float]:
    """annual() plus the loud failure on the UK's empty-cube traps."""
    s = annual(dataset, **filters)
    if not s:
        raise RuntimeError(f"{dataset} {filters}: empty result")
    return s


def rows(years, columns: dict[str, dict[int, float]],
         dec: int | dict[str, int] = 2) -> str:
    """A wide CSV: one row per year, blanks where the source has no value.

    `dec` is one precision for every column, or {column: precision}.
    """
    head = "year," + ",".join(columns)
    lines = [head]
    for y in years:
        cells = []
        for col, s in columns.items():
            v = s.get(y)
            d = dec[col] if isinstance(dec, dict) else dec
            cells.append("" if v is None else f"{v:.{d}f}")
        lines.append(f"{y}," + ",".join(cells))
    return "\n".join(lines) + "\n"


def write(rel: str, text: str) -> None:
    path = DATA / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    print(f"  -> data/{rel}")


def year_span(columns: dict[str, dict[int, float]]) -> list[int]:
    """min..max populated year across the columns: the file's own coverage,
    with interior holes carried as blank rows."""
    ys = [y for s in columns.values() for y in s]
    return list(range(min(ys), max(ys) + 1))


def migration(dataset: str, dim: str, name: str,
              agedef: bool = False) -> dict[str, dict[int, float]]:
    """The four CUTS of one migration dataset as {column: {year: value}}.

    No unit filter (the UK trap: unit=PER empties these cubes). Flow
    datasets (and migr_acq) carry an `agedef` dimension the stock ones do
    not; it is pinned to REACH where it exists.
    """
    out = {}
    for col, code in CUTS.items():
        extra = {"agedef": "REACH"} if agedef else {}
        out[f"{name}_{col}"] = series(dataset, geo=GEO, sex="T", age="TOTAL",
                                      freq="A", **{dim: code}, **extra)
    return out


def check(ok: bool, what: str) -> None:
    """A pinned-value assertion that survives `python3 -O`."""
    if not ok:
        raise SystemExit(f"pinned check failed: {what} — not writing")


def pinned(s: dict[int, float], year: int, want: int, tag: str) -> None:
    got = s.get(year)
    print(f"  check {tag} {year}: {got} (pinned {want})")
    check(got == want, f"{tag} {year} = {got}, expected {want}")


def hole(s: dict[int, float], year: int, tag: str) -> None:
    """A published gap stays a gap: no cell, so the CSV carries a blank."""
    check(year not in s, f"{tag} {year} is populated — the known hole closed")
    print(f"  check {tag} {year}: blank (hole kept)")


def frozen(columns: dict[str, dict[int, float]], last: int, tag: str) -> None:
    """The segment ends by design; a revived series must fail here."""
    latest = max(y for s in columns.values() for y in s)
    if latest != last:
        raise RuntimeError(f"{tag}: expected the series to end at {last}, "
                           f"got data for {latest}")


def main() -> None:
    print("Fetching Eurostat series for the United Kingdom...")

    # ---- migration segment 1 of 3: the IPS era, frozen at 2019 ---------
    imm = migration("migr_imm1ctz", "citizen", "immigration_by_citizenship",
                    agedef=True)
    imm_birth = migration("migr_imm3ctb", "c_birth", "immigration_by_birth",
                          agedef=True)
    emi = migration("migr_emi1ctz", "citizen", "emigration_by_citizenship",
                    agedef=True)
    flows = {**imm, **imm_birth, **emi}
    pinned(imm["immigration_by_citizenship_total"], 2019, 680906, "immigration")
    pinned(emi["emigration_by_citizenship_total"], 2019, 368385, "emigration")
    # The 2005 hole is real; it stays a blank row.
    hole(imm["immigration_by_citizenship_total"], 2005, "immigration")
    frozen(flows, 2019, "migration flows")
    write("migration/flows_from_estat.csv", rows(year_span(flows), flows,
                                               dec=0))

    stock = migration("migr_pop1ctz", "citizen", "stock_by_citizenship")
    stock_birth = migration("migr_pop3ctb", "c_birth", "stock_by_birth")
    stocks = {**stock, **stock_birth}
    pinned(stock["stock_by_citizenship_total"], 2019, 66647112,
           "stock (citizenship frame)")
    for y in (2000, 2002):
        hole(stock["stock_by_citizenship_total"], y, "stock (citizenship frame)")
    frozen(stocks, 2019, "migration stocks")
    write("migration/stocks_from_estat.csv", rows(year_span(stocks), stocks,
                                                dec=0))

    # Asylum: the applicant dimension has three codes (FRST, SSEQ, TOTAL)
    # and must be pinned; applications are not decisions or people present.
    asy = {"applications": series("migr_asyappctza", geo=GEO,
                                  citizen="TOTAL", applicant="TOTAL", sex="T",
                                  age="TOTAL", freq="A"),
           "first_time": series("migr_asyappctza", geo=GEO, citizen="TOTAL",
                                applicant="FRST", sex="T", age="TOTAL",
                                freq="A")}
    pinned(asy["applications"], 2019, 46130, "asylum applications")
    pinned(asy["first_time"], 2019, 44315, "asylum first-time")
    frozen(asy, 2019, "asylum applications")
    write("migration/asylum_from_estat.csv", rows(year_span(asy), asy, dec=0))

    # First residence permits: NO sex dimension on this dataset (sex=T is a
    # 400 INVALID_QUERY_DIMENSION), and coverage stops a year earlier.
    permits = {"first_permits": series("migr_resfirst", geo=GEO,
                                       citizen="TOTAL", reason="TOTAL",
                                       duration="TOTAL", freq="A")}
    pinned(permits["first_permits"], 2018, 450775, "first permits")
    frozen(permits, 2018, "first residence permits")
    write("migration/permits_from_estat.csv", rows(year_span(permits),
                                                   permits, dec=0))

    # Naturalisation: the flow that shrinks the foreign-citizen stock
    # without anybody moving.
    acq = {"acquisitions": series("migr_acq", geo=GEO, citizen="TOTAL",
                                  sex="T", age="TOTAL", agedef="REACH",
                                  freq="A")}
    pinned(acq["acquisitions"], 2019, 159348, "acquisitions")
    frozen(acq, 2019, "acquisitions of citizenship")
    write("migration/naturalisation_from_estat.csv", rows(year_span(acq),
                                                          acq, dec=0))

    # ---- demography: the one Eurostat family still current for the UK --
    # 1-January stocks and counts, drawn beside the ONS mid-year estimates,
    # never spliced with them. Full observed range; the plates clip.
    pop = series("demo_gind", geo=GEO, indic_de="JAN", freq="A")
    births = series("demo_gind", geo=GEO, indic_de="LBIRTH", freq="A")
    deaths = series("demo_gind", geo=GEO, indic_de="DEATH", freq="A")
    # Fertility (demo_find) froze earlier than the vital counts: it ends
    # 2018, and the tail years stay blank.
    tfr = series("demo_find", geo=GEO, indic_de="TOTFERRT", freq="A")
    pinned(pop, 2026, 69554275, "population 1 January")
    demo = {"pop_mn": {y: v / 1e6 for y, v in pop.items()},
            "births": births, "deaths": deaths, "tfr": tfr}
    write("demography/demography_from_estat.csv",
          rows(year_span(demo), demo,
               dec={"pop_mn": 6, "births": 0, "deaths": 0, "tfr": 2}))

    print("Done. Diff the *_from_estat.csv sidecars before adopting.")


if __name__ == "__main__":
    main()
