"""Department of Health — registered deaths by leading cause.

    python3 -m countries.hongkong.fetch.fetch_dh [--offline]

Writes the review sidecar `data/mortality/causes_from_dh.csv` only.

Route: `data.gov.hk` (CKAN) -> dataset `hk-dh-dh_ncddhss-ncdd-dataset-3`
("Death Statistics") -> the English CSV
`https://www.dh.gov.hk/datagovhk/ncdd/Number of Registered Deaths by Leading
Cause of Death, 2001 to 2024 (EN).csv`. The file is a presentation table, not
an API: a BOM, a title row, a note block, then a header row whose columns are
years, with figures written with a space as the thousands separator.

Two facts in the table's own notes matter for the plate:

* from 2001 the ranking uses ICD-10, so the table is internally comparable
  only from 2001 (the previous table used ICD-9);
* COVID-19 was coded to J98.8 up to 2023 and to U07.1/U07.2 from 2024, so the
  series is continuous in intent but the code behind it changes in 2024. The
  note is reproduced in DATA_NOTES.md.

"External causes of morbidity and mortality (V01-Y89)" is a single row: it
contains suicides, road deaths and falls together, so it cannot be published
as a suicide rate. That is why the security chapter's suicide panel is
pending rather than filled from this file.
"""
from __future__ import annotations

import csv
import io
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "dh"
DATA = ROOT / "data"

URL = ("https://www.dh.gov.hk/datagovhk/ncdd/"
       "Number%20of%20Registered%20Deaths%20by%20Leading%20Cause%20of%20Death,"
       "%202001%20to%202024%20(EN).csv")
UA = {"User-Agent": "curl/8.5.0"}

# Known registered deaths, all causes: 2003 (SARS year) and 2022 (the
# Omicron wave, the highest annual total on record).
PINS = {2003: 36423, 2022: 61557}


class FetchError(SystemExit):
    pass


def fail(msg: str) -> None:
    print(f"fetch_dh: {msg}", file=sys.stderr)
    sys.exit(1)


def payload(offline: bool) -> bytes:
    cache_file = CACHE / "leading_causes.csv"
    if cache_file.exists():
        return cache_file.read_bytes()
    if offline:
        fail(f"offline and no cached file {cache_file}")
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(URL, headers=UA)
            with urllib.request.urlopen(req, timeout=120) as r:
                body = r.read()
            if body[:4].lower() in (b"<htm", b"<!do"):
                raise ValueError("HTML where a CSV was expected")
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_bytes(body)
            return body
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(3 * (attempt + 1))
    fail(f"{URL}: {last}")


def number(cell: str) -> str:
    """'11 406' -> '11406'; '-' and blanks -> '' (missing, never zero)."""
    cell = (cell or "").replace("\xa0", " ").strip()
    if cell in ("", "-", "N.A.", "NA"):
        return ""
    cell = cell.replace(" ", "").replace(",", "")
    if not re.fullmatch(r"-?\d+(?:\.\d+)?", cell):
        raise FetchError(f"unparseable figure {cell!r}")
    return cell


def main(argv: list[str]) -> None:
    offline = "--offline" in argv
    text = payload(offline).decode("utf-8-sig", "replace")
    rows = list(csv.reader(io.StringIO(text)))
    head_at = next((i for i, r in enumerate(rows)
                    if r and r[0].strip().lower() == "cause of death"), None)
    if head_at is None:
        fail("no 'Cause of death' header row — the table changed shape")
    header = rows[head_at]
    years = [(i, int(c)) for i, c in enumerate(header)
             if c.strip().isdigit() and 1990 <= int(c) <= 2100]
    if not years or years[0][1] != 2001:
        fail(f"expected years from 2001, header has {header[:4]}")

    out_rows, seen = [], {}
    for r in rows[head_at + 1:]:
        if not r or not r[0].strip():
            continue
        label = r[0].replace("\xa0", " ").strip()
        if label.lower().startswith(("notes", "the figures", "- ")) or ":" in label[:8]:
            continue
        for i, year in years:
            value = number(r[i] if i < len(r) else "")
            if value == "":
                continue
            out_rows.append((year, label, value))
            if label.lower().startswith("all causes"):
                seen[year] = float(value)
    if not out_rows:
        fail("no observations parsed")
    for year, want in PINS.items():
        got = seen.get(year)
        if got is None or abs(got - want) > 0.5:
            fail(f"all-cause deaths {year} = {got!r}, expected {want}")

    out = DATA / "mortality/causes_from_dh.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["year", "cause", "deaths"])
        for year, label, value in sorted(out_rows, key=lambda x: (x[0], x[1])):
            w.writerow([year, label, value])
    print(f"  {out.relative_to(ROOT)}  ({len(out_rows)} rows, "
          f"{years[0][1]}-{years[-1][1]}, {len(set(r[1] for r in out_rows))} "
          "causes)")


if __name__ == "__main__":
    main(sys.argv[1:])
