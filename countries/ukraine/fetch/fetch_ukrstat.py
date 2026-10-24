"""Ukrstat (SSSU) population, from the SDMX 2.1 dataflow.

    python3 -m countries.ukraine.fetch.fetch_ukrstat [--offline]

Writes the review sidecar `demography/population_ukrstat_from_sssu.csv`;
it never writes a curated file (SOURCING_A_COUNTRY.md §4).

The endpoint is the one the publisher documents on its own API page:

    https://stat.gov.ua/sdmx/workspaces/default:integration/registry/
        sdmx/2.1/dataflow/SSSU/DF_POPULATION_STRUCTURE/8.0.0

`stat.gov.ua` answers HTTP 403 "The request is blocked" to this network
(WAF; DISCOVERY.md records the probe), so the discovery pass retrieved the
dataflow payload once and left it in the cache this fetcher reads. The
series is chosen by key rather than by position:

    0:0:0:0:2:0
    INDICATOR=PNMI_01 (total population), REGION=UA national,
    AGE=_T, GENDER=_T, TERRAIN_TYPE=_T, FREQ=A

The 2015 seam is real and belongs to the publisher: Ukrstat excludes the
temporarily occupied territories from its 2015-on register (the file's
own note says so), while the World Bank series includes them throughout.
The two lines are never spliced.
"""
from __future__ import annotations

import csv
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "ukrstat" / "population_size_structure.json"
OUT = ROOT / "data" / "demography" / "population_ukrstat_from_sssu.csv"
URL = ("https://stat.gov.ua/sdmx/workspaces/default:integration/registry/"
       "sdmx/2.1/dataflow/SSSU/DF_POPULATION_STRUCTURE/8.0.0?detail=full"
       "&references=none")
KEY = "0:0:0:0:2:0"

# Known values, asserted before anything is written: the national total in
# the 1989 census year and the last register year before the full-scale
# invasion. A payload that moves them is not this series.
KNOWN = {"1989": 51706700.0, "2021": 41588354.0}


class FetchError(SystemExit):
    pass


def fail(msg: str) -> None:
    print(f"fetch_ukrstat: {msg}", file=sys.stderr)
    sys.exit(1)


def payload(offline: bool) -> dict:
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    if offline:
        fail(f"no cache at {CACHE} and --offline was given; nothing written")
    try:
        with urllib.request.urlopen(URL, timeout=45) as fh:
            body = fh.read()
    except Exception as exc:                       # noqa: BLE001
        fail(f"{URL} failed: {type(exc).__name__}: {exc}; nothing written")
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_bytes(body)
    return json.loads(body)


def series(raw: dict) -> dict[str, float]:
    try:
        data = raw["data"]
        dims = data["structures"][0]["dimensions"]
        time = [v["value"] for v in dims["observation"][0]["values"]]
        ser = data["dataSets"][0]["series"][KEY]
    except (KeyError, IndexError, TypeError) as exc:
        fail(f"payload shape is not the SDMX dataflow: {exc!r}")
    out = {}
    for idx, obs in ser["observations"].items():
        period = time[int(idx)]
        if len(period) == 4 and period.isdigit() and obs and obs[0]:
            out[period] = float(obs[0])
    if len(out) < 30:
        fail(f"only {len(out)} annual observations; expected 34")
    for year, want in KNOWN.items():
        got = out.get(year)
        if got != want:
            fail(f"known value {year}: got {got!r}, expected {want}")
    return out


def main(argv: list[str]) -> int:
    raw = payload("--offline" in argv)
    obs = series(raw)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["year", "population"])
        for year in sorted(obs):
            w.writerow([year, f"{obs[year]:.0f}"])
    print(f"wrote {OUT.relative_to(ROOT.parent.parent)} "
          f"({len(obs)} years, {min(obs)}-{max(obs)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
