"""The committed CSVs, checked as data rather than as text.

Every plate is drawn from these files and nothing else, so a silent defect
here — a duplicated year, a column of blanks, a placeholder someone left in
a cell — becomes a published number without passing through anyone's eyes.
These are the checks the five original projects each ran on their own data;
they are written once here and applied to all five.
"""
from __future__ import annotations

import csv
import math
import re
from pathlib import Path

import pytest

PLACEHOLDERS = {"na", "n/a", "nan", "null", "none", "-", "--", "?", "tbd",
                "todo", "x", ".", "..", "...", "#n/a", "#value!", "#ref!"}


def _csvs(country):
    return sorted(country.data_dir.rglob("*.csv"))


def _rows(path: Path):
    """A CSV's data rows, skipping the '#' provenance header some carry.

    The comment lines are how a file's caveats travel with the data; they
    are not rows, and reading them as rows is how a provenance note turns
    into a year.
    """
    with path.open(encoding="utf-8", newline="") as fh:
        lines = [ln for ln in fh if not ln.lstrip().startswith("#")]
    return list(csv.DictReader(lines))


def test_the_country_has_data_at_all(country):
    assert _csvs(country), f"{country.slug}: no CSVs under data/"


def test_every_csv_parses_and_has_a_header(country):
    for path in _csvs(country):
        rows = _rows(path)
        rel = path.relative_to(country.data_dir)
        assert rows, f"{country.slug}/{rel}: no data rows"
        assert all(k for k in rows[0]), \
            f"{country.slug}/{rel}: a column has no name"


def test_every_row_has_every_column(country):
    """A short row makes DictReader invent a None, which reads as a blank.

    A blank means "the publisher has not filled this year"; a row that is
    simply truncated means something else, and the two must not look the
    same.
    """
    for path in _csvs(country):
        rel = path.relative_to(country.data_dir)
        for i, row in enumerate(_rows(path), start=2):
            assert None not in row, \
                f"{country.slug}/{rel}:{i}: more cells than columns"
            short = [k for k, v in row.items() if v is None]
            assert not short, \
                f"{country.slug}/{rel}:{i}: missing cells for {short}"


def test_years_are_ordered_and_plausible(country):
    # Wider than the plate window on purpose: several countries commit an
    # official population projection that runs decades past the last plate
    # year, and a historical series may start long before the first. What
    # this catches is a year that is not one — 20224, 1066, 0.
    span = range(1850, 2200)
    for path in _csvs(country):
        rows = _rows(path)
        rel = path.relative_to(country.data_dir)
        if not rows or "year" not in rows[0]:
            continue
        years = []
        for row in rows:
            cell = (row.get("year") or "").strip()
            if not cell:
                continue
            assert re.fullmatch(r"-?\d{4}", cell), \
                f"{country.slug}/{rel}: year {cell!r} is not a year"
            years.append(int(cell))
        assert years == sorted(years), f"{country.slug}/{rel}: years out of order"
        bad = [y for y in years if y not in span]
        assert not bad, f"{country.slug}/{rel}: implausible years {bad[:5]}"


def test_no_row_is_silently_duplicated(country):
    """Two rows for one key are two answers to one question.

    Long-format files key on a year plus a category, so the key is every
    column that is not a number — that is what makes a row unique.
    """
    for path in _csvs(country):
        rows = _rows(path)
        rel = path.relative_to(country.data_dir)
        if not rows:
            continue
        keys = [c for c in rows[0]
                if c == "year" or not _mostly_numeric(rows, c)]
        if "year" not in keys:
            continue
        seen = {}
        for i, row in enumerate(rows, start=2):
            k = tuple((row.get(c) or "").strip() for c in keys)
            assert k not in seen, \
                f"{country.slug}/{rel}: rows {seen[k]} and {i} share key {k}"
            seen[k] = i


def _mostly_numeric(rows, column) -> bool:
    vals = [(r.get(column) or "").strip() for r in rows]
    filled = [v for v in vals if v]
    if not filled:
        return False
    ok = 0
    for v in filled:
        try:
            float(v)
            ok += 1
        except ValueError:
            pass
    return ok >= len(filled) * 0.8


def test_no_cell_holds_a_placeholder_instead_of_a_blank(country):
    """A missing year is an empty cell, not the word for one.

    "NA" in a numeric column either crashes the reader or, worse, is read
    as text and silently dropped, so the plate draws a gap the publisher
    never left.
    """
    for path in _csvs(country):
        rel = path.relative_to(country.data_dir)
        rows = _rows(path)
        numeric_cols = [c for c in (rows[0] if rows else {})
                        if c != "year" and _mostly_numeric(rows, c)]
        for i, row in enumerate(rows, start=2):
            for c in numeric_cols:
                v = (row.get(c) or "").strip().lower()
                assert v not in PLACEHOLDERS, \
                    f"{country.slug}/{rel}:{i}: {c} = {v!r}; leave it blank"


def test_no_column_is_entirely_empty(country):
    """A column of blanks is a promise the data does not keep."""
    for path in _csvs(country):
        rel = path.relative_to(country.data_dir)
        rows = _rows(path)
        if not rows:
            continue
        for c in rows[0]:
            filled = [r for r in rows if (r.get(c) or "").strip()]
            assert filled, f"{country.slug}/{rel}: column {c!r} is empty"


def test_numbers_are_written_without_thousands_separators(country):
    """A CSV is machine input; 1,234 in a cell is two cells or a string."""
    for path in _csvs(country):
        rel = path.relative_to(country.data_dir)
        rows = _rows(path)
        for i, row in enumerate(rows, start=2):
            for c, v in row.items():
                v = (v or "").strip()
                if re.fullmatch(r"-?\d{1,3}(,\d{3})+(\.\d+)?", v):
                    pytest.fail(f"{country.slug}/{rel}:{i}: {c} = {v!r}")


def test_the_reader_agrees_with_the_file(country):
    """core.plotting.read_table is the only CSV reader; it must round-trip.

    Every plate goes through it, so a file it reads differently from the
    bytes on disk is a file whose published numbers nobody can check.
    """
    for path in _csvs(country):
        rel = str(path.relative_to(country.data_dir))
        table = country.table(rel)
        assert table is not None, f"{country.slug}/{rel}: unreadable"
        rows = _rows(path)
        assert len(next(iter(table.values()))) == len(rows), \
            f"{country.slug}/{rel}: reader saw a different number of rows"
        if "year" in table:
            on_disk = [int(r["year"]) for r in rows if (r.get("year") or "").strip()]
            read = [int(y) for y in table["year"] if y is not None
                    and not (isinstance(y, float) and math.isnan(y))]
            assert read == on_disk, f"{country.slug}/{rel}: years differ"
