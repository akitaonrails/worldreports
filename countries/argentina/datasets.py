"""Read the committed CSVs. Nothing in this atlas reads an API at draw time.

Every chart is built from `data/**/*.csv`, which are the files a reviewer
can diff. The fetchers write `*_check.csv` sidecars beside them and never
overwrite a curated number, so a bad upstream day cannot silently rewrite
a published plate.
"""
from __future__ import annotations

import csv
from pathlib import Path

from core import country as _boundary

# This module lives beside the data it reads, inside countries/argentina/.
# That makes reaching another country's files awkward but not impossible —
# a `rel` carrying `..` would still escape — so every path below is
# resolved through core.country.within, the same check the shared
# accessors use. Living next to the data is the intent; the check is what
# enforces it.
ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"


def path(rel: str) -> Path:
    """One of this country's CSVs, refusing anything outside its data/.

    Called through the module rather than bound by name on import, so the
    one check stays one check: core.provenance watches reads by replacing
    `core.country.within`, and a `from ... import within` here would hold
    the original and read unwatched.
    """
    return _boundary.within(DATA, rel, "argentina")

# Every plate shares one horizontal axis, so a reader can carry a date
# across panels without re-reading the ticks.
YEARS = list(range(2006, 2027))
FIRST_YEAR, LAST_YEAR = YEARS[0], YEARS[-1]


def load(rel: str) -> dict[str, dict[int, float]]:
    """A CSV keyed year -> value, one inner dict per numeric column.

    A column that does not parse as a number is reported as an empty dict
    rather than raising: the long-format files carry a text key column
    beside their value column, and `load_long` is the reader for those.
    """
    out: dict[str, dict[int, float]] = {}
    with path(rel).open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        columns = [c for c in (reader.fieldnames or []) if c != "year"]
        out = {c: {} for c in columns}
        for row in reader:
            try:
                year = int(row["year"])
            except (TypeError, ValueError):
                continue
            for column in columns:
                cell = (row.get(column) or "").strip()
                if not cell:
                    continue
                try:
                    out[column][year] = float(cell)
                except ValueError:
                    continue
    return out


def load_long(rel: str, key: str, value: str) -> dict[str, dict[int, float]]:
    """A long-format CSV (year, <key>, <value>) as one dict per key."""
    out: dict[str, dict[int, float]] = {}
    with path(rel).open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            cell = (row.get(value) or "").strip()
            if not cell:
                continue
            out.setdefault(row[key], {})[int(row["year"])] = float(cell)
    return out


def xy(series: dict[int, float], lo: int = FIRST_YEAR, hi: int = LAST_YEAR
       ) -> tuple[list[int], list[float]]:
    """Years and values inside the window, in order, blanks dropped."""
    years = [y for y in sorted(series) if lo <= y <= hi]
    return years, [series[y] for y in years]


def xy_gapped(series: dict[int, float], lo: int = FIRST_YEAR,
              hi: int = LAST_YEAR) -> tuple[list[int], list[float]]:
    """Like `xy`, but a missing year inside the range becomes a break.

    Plotting only the years that exist makes matplotlib draw a straight
    segment across the hole, which is the one thing this atlas must never
    do: a line joining 2007 to 2016 across the INDEC intervention asserts
    that the decade between them was measured. It was not.
    """
    present = [y for y in sorted(series) if lo <= y <= hi]
    if not present:
        return [], []
    years = list(range(present[0], present[-1] + 1))
    return years, [series.get(y, float("nan")) for y in years]


def last_year_with(series: dict[int, float]) -> int:
    return max(series)
