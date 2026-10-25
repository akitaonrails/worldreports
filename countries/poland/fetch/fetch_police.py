#!/usr/bin/env python3
"""Refresh Poland's police-recorded homicide count.

Usage:  make C=poland fetch   (or: python3 -I fetch/fetch_police.py)

The Polish Police publish annual statistics per offence category as XLSX
attachments: confirmed offences (przestępstwa stwierdzone — the count the
police clear, which includes ATTEMPTS) and proceedings initiated
(postępowania wszczęte — the count that follows a report). Both run from
1999 to the last published year.

This is the NATIONAL line for the security chapter's homicide slot, and
it is not the death count: the vital-statistics series in
security_from_estat.csv counts bodies (assault deaths, ICD X85–Y09) and
is roughly a third of the police count, because an attempt is an offence
and not a death. The two are drawn as separate, labelled lines; neither
is wrong and neither may be spliced into the other.

The Police portal is a JS app whose tables are served as attachments —
the file links are found on the offence page, not guessed.

Output: security/homicide_from_police.csv (review sidecar only).
"""
from __future__ import annotations

import io
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, FetchError, assert_close, get, write_csv  # noqa: E402

PAGE = ("https://statystyka.policja.pl/st/przestepstwa-ogolem/"
        "przestepstwa-kryminalne/zabojstwo")
#: The two attachments the page carries, matched by their file names.
WANTED = {
    "confirmed": "przestepstwa-zabojstwo",
    "initiated": "postepowania-wszczete-przestepstwa-zabojstwo",
}


def links() -> dict[str, str]:
    html = get(PAGE, suffix=".html", timeout=120).decode("utf-8", "replace")
    found = {}
    for href in re.findall(r'href="([^"]*\.xlsx)"', html):
        for key, stem in WANTED.items():
            if stem in href and key not in found:
                found[key] = (href if href.startswith("http")
                              else "https://statystyka.policja.pl" + href)
    missing = set(WANTED) - set(found)
    if missing:
        raise FetchError(f"police: attachments missing for {missing}")
    return found


def national(url: str) -> dict[int, float]:
    """{year: count} for the 'Polska' rows of one attachment."""
    body = get(url, suffix=".xlsx", timeout=180)
    if not zipfile.is_zipfile(io.BytesIO(body)):
        raise FetchError(f"police {url}: not an XLSX (HTML error page?)")
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(body), data_only=True)
    ws = wb.worksheets[0]
    out: dict[int, float] = {}
    for row in ws.iter_rows(values_only=True):
        if not row or len(row) < 3:
            continue
        # The confirmed-offence sheet labels the national rows "Polska";
        # the proceedings sheet instead writes "jednostki organizacyjne
        # Policji" over the whole-country aggregate, so the national test
        # is "this row is not a regional unit". Both sheets have exactly
        # one such label, and a per-voivodeship row always names its unit.
        unit = str(row[0] or "").strip().casefold()
        year = str(row[1] or "").strip()
        national = unit.startswith("polska") or unit.startswith(
            "jednostki organizacyjne")
        if not national or not year.isdigit():
            continue
        try:
            out[int(year)] = float(row[2])
        except (TypeError, ValueError):
            continue
    if not out:
        raise FetchError(f"police {url}: no national rows")
    return out


def main() -> None:
    print("Fetching police-recorded homicide for Poland...")
    urls = links()
    confirmed = national(urls["confirmed"])
    initiated = national(urls["initiated"])
    # Known value: 559 confirmed homicides in 2023 (attempts included),
    # and 2022 = 499 — the two the police's own table prints.
    assert_close(confirmed.get(2023), 559, 0.5, "police homicide 2023")
    assert_close(confirmed.get(2022), 499, 0.5, "police homicide 2022")

    header = ["year", "homicides_confirmed", "proceedings_initiated"]
    rows = []
    for y in range(1999, 2027):
        rows.append([y, int(confirmed[y]) if y in confirmed else None,
                     int(initiated[y]) if y in initiated else None])
    path = write_csv("security/homicide_from_police.csv", header, rows,
                     comment="""
Polish Police, "Zabójstwo" (homicide) annual statistics, whole country.
homicides_confirmed = przestępstwa stwierdzone (confirmed offences —
INCLUDES ATTEMPTS, which is why it is far above the death count);
proceedings_initiated = postępowania wszczęte.
National police series, 1999 to the last published year. The
vital-statistics assault-death count is in security_from_estat.csv; the
two are different questions and are two lines.
Source: statystyka.policja.pl, attachments reached from the offence page.
""")
    print(f"  -> {path.relative_to(DATA)}")
    print("Done. Diff the *_from_police.csv sidecar before adopting.")


if __name__ == "__main__":
    main()
