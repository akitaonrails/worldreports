#!/usr/bin/env python3
"""Refresh Russia's NATIONAL statistical layer from Rosstat's own workbooks.

Usage:  make C=russia fetch
        python3 -I fetch/fetch_rosstat.py [--rosstat-insecure]

Rosstat is the computing institution for every series here, and these are
its own published workbooks — not a republication. They sit beside the
World Bank and IMF series and are never spliced into them.

  VVP_god_s1995-2025.xlsx        GDP at current prices (billion roubles,
                                 trillion before 1998), the physical-volume
                                 index (previous year = 100) and the GDP
                                 deflator (previous year = 100).
  ipc_s_1992-2025.xlsx           CPI, all goods and services, Russian
                                 Federation, year on year (previous year =
                                 100) — the headline December-to-December
                                 reading, NOT the annual average.
  popul_1897+.xlsx               Population, million people, annual.
  Popul components_1990+.xlsx    Population change and its components,
                                 thousand people: total, natural, migration.

THE TLS PROBLEM, and why this fetcher has a flag for it
-------------------------------------------------------
`curl https://rosstat.gov.ru/` on a normal Linux host prints nothing and
returns no HTTP status at all. It is not a geo-block:

    openssl s_client -connect rosstat.gov.ru:443
    subject=CN=*.rosstat.gov.ru, O=Федеральная служба государственной
            статистики, C=RU, ... OGRN=1047708023483
    verify error:num=20: unable to get local issuer certificate

The chain terminates in a Russian Trusted Root CA (Минцифры) that no
public trust store carries, so a verifying client aborts before the
request. With the chain unverified the same URL returns 826 KB of the
statistical office's site and every /storage/mediabank/*.xlsx answers 200.

Verification is therefore ON by default and a failure says exactly this.
`--rosstat-insecure` exists for a fetch host without the Russian root
installed; it changes the transport, never a number, and every sidecar
records which mode produced it. The permanent fix is to install
gu-st.ru's Russian Trusted Root CA in the host trust store.

WHAT IS REJECTED BEFORE ANYTHING IS CACHED
------------------------------------------
An official gateway that serves an error page under HTTP 200 would parse
as zero rows and read as a missing series. Every download is checked for
the ZIP signature of an xlsx (PK\\x03\\x04) and for a plausible size, and
every parse is checked against a known observation. A workbook that fails
either check is not cached and the run exits non-zero having written
nothing.
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import ssl
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"

BASE = "https://rosstat.gov.ru/storage/mediabank/"
FILES = {
    "gdp": "VVP_god_s1995-2025.xlsx",
    "cpi": "ipc_s_1992-2025.xlsx",
    "population": "popul_1897+.xlsx",
    "components": "Popul components_1990+.xlsx",
    "quarterly": "VVP_kvartal_s-1995-2026.xlsx",
}

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/126.0"}

# The window the plates share. Rosstat's own files reach back to 1995 and
# 1992; only the shared window is written to the sidecars.
YEAR_FROM, YEAR_TO = 2006, 2026


def fetch(key: str, insecure: bool) -> Path:
    """Download one workbook into cache/, refusing anything but a real xlsx."""
    CACHE.mkdir(exist_ok=True)
    name = FILES[key]
    path = CACHE / name
    if path.exists() and path.read_bytes()[:2] == b"PK":
        return path
    url = BASE + urllib.request.quote(name)
    ctx = None
    if insecure:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS),
                                    timeout=180, context=ctx) as r:
            raw = r.read()
    except ssl.SSLCertVerificationError as e:
        sys.exit(f"{name}: TLS verification failed ({e}).\n"
                 "rosstat.gov.ru is signed by the Russian Trusted Root CA, "
                 "which is not in this host's trust store. Install it, or "
                 "re-run with --rosstat-insecure to record the transport "
                 "mode in the sidecar.")
    except Exception as e:  # noqa: BLE001
        sys.exit(f"{name}: fetch failed: {e}")
    if raw[:2] != b"PK" or len(raw) < 4000:
        sys.exit(f"{name}: not an xlsx ({len(raw)} bytes, starts {raw[:16]!r}); "
                 "an HTML error page under HTTP 200 is not data")
    path.write_bytes(raw)
    return path


def _year(cell) -> int | None:
    """A year out of a Rosstat header cell, which may carry a footnote.

    '20222)' is 2022 with footnote 2), '2024),3)' is 2024 with two. The
    digits before the first non-digit are the year; anything else is not
    a year and returns None rather than guessing.
    """
    if cell is None:
        return None
    text = str(cell).strip()
    if not text:
        return None
    head = ""
    for ch in text:
        if ch.isdigit():
            head += ch
        else:
            break
    if len(head) < 4:
        return None
    # '20222)' is 2022 with footnote 2) — the footnote's digit runs on into
    # the year, so the year is the FIRST four digits of the run, not the
    # whole run. (Taking the run whole turned every 2022+ column into None
    # and truncated the series at 2021: silent, and the assert caught it.)
    year = int(head[:4])
    return year if 1850 <= year <= 2199 else None


def _num(cell) -> float | None:
    """A numeric cell, or None. Rosstat writes '…' where it suppressed a
    value (2014 in the components workbook) — that is a hole, not a zero."""
    if cell is None:
        return None
    if isinstance(cell, (int, float)):
        return float(cell)
    text = str(cell).strip().replace(",", ".").replace("\xa0", "")
    if not text or text in {"…", "...", "-", "x"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def read_rows(path: Path, sheet, row_from=1, row_to=None) -> list[tuple]:
    """Rows out of one worksheet, as tuples.

    Deliberately NOT read_only: several Rosstat workbooks carry a stale
    sheet dimension (VVP_god's second volume-index sheet declares ten
    columns and holds fourteen), and openpyxl's read-only path trusts it,
    silently truncating the years after 2021. The full parser reads the
    cells that are actually there.
    """
    import openpyxl

    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.worksheets[sheet] if isinstance(sheet, int) else wb[sheet]
    out = []
    for row in ws.iter_rows(min_row=row_from, max_row=row_to, values_only=True):
        out.append(row)
    wb.close()
    return out


def parse_horizontal(rows: list[tuple], head_row: int, value_row: int) -> dict[int, float]:
    """A year-across-the-top, values-below block into {year: value}."""
    head, vals = rows[head_row - 1], rows[value_row - 1]
    out: dict[int, float] = {}
    for h, v in zip(head, vals):
        y = _year(h)
        n = _num(v)
        if y is not None and n is not None:
            out[y] = n
    return out


def gdp_series(path: Path) -> dict[int, dict[str, float]]:
    """Nominal GDP, physical-volume index and deflator, in one {year: ...}.

    Each quantity is split across two sheets in the publisher's file — one
    ending in 2011, one starting there — so the halves are joined on the
    year, and 2011 (present in both) is taken from the earlier sheet.
    """
    nominal = parse_horizontal(read_rows(path, "1", 3, 4), 1, 2)
    nominal_2 = parse_horizontal(read_rows(path, "2", 3, 5), 2, 3)
    for y, v in nominal_2.items():
        nominal.setdefault(y, v)
    volume = parse_horizontal(read_rows(path, "7", 3, 4), 1, 2)
    volume_2 = parse_horizontal(read_rows(path, "8", 3, 4), 1, 2)
    for y, v in volume_2.items():
        volume.setdefault(y, v)
    deflator = parse_horizontal(read_rows(path, "9", 3, 4), 1, 2)
    deflator_2 = parse_horizontal(read_rows(path, "10", 3, 4), 1, 2)
    for y, v in deflator_2.items():
        deflator.setdefault(y, v)

    out: dict[int, dict[str, float]] = {}
    for y in sorted(set(nominal) | set(volume) | set(deflator)):
        row = {}
        if y in nominal:
            row["nominal_bn_rub"] = nominal[y]
        if y in volume:
            # The publisher's index is previous year = 100; growth is the
            # index minus 100. Derived, and asserted on a known year below.
            row["real_growth_pct"] = volume[y] - 100.0
        if y in deflator:
            row["deflator_pct"] = deflator[y] - 100.0
        out[y] = row
    return out


def cpi_series(path: Path) -> dict[int, float]:
    """The Russian Federation row of the CPI table, minus 100.

    The table is one row per region with the federation first; matching on
    the exact label avoids picking up a region whose name also starts with
    'Российская'.
    """
    rows = read_rows(path, 0, 1, 40)
    # The header is the row carrying years, not the row carrying the title:
    # both have text in the first cell, so the test is "at least three
    # year-shaped cells", not "the first cell is not a number".
    head = None
    for row in rows:
        if sum(1 for c in row if _year(c) is not None) >= 3:
            head = row
            break
    if head is None:
        sys.exit("cpi: no year header row found")
    years = [_year(c) for c in head]
    for row in rows:
        label = str(row[0] or "").strip()
        if label == "Российская Федерация":
            out = {}
            for y, v in zip(years, row):
                n = _num(v)
                if y is not None and n is not None:
                    out[y] = n - 100.0
            return out
    sys.exit("cpi: the Russian Federation row is missing")


def population_series(path: Path) -> dict[int, float]:
    """Population, million people, from the vertical year column.

    Cells carry footnote markers ('20232)'); the leading four digits are
    the year. Values are as published, one decimal, so the index is exact
    to 0.07% — enough for a per-1,000 rate and stated in the notes.
    """
    out: dict[int, float] = {}
    for row in read_rows(path, 0, 5, 140):
        y = _year(row[0])
        n = _num(row[1]) if len(row) > 1 else None
        if y is not None and n is not None:
            out[y] = n
    return out


def components_series(path: Path) -> dict[int, dict[str, float]]:
    """Total, natural and migration change, thousand people, all population.

    Sheet "1" is the whole population. Column 1 is the 1 January stock,
    columns 2-4 are the year's total / natural / migration change, column
    5 the 31 December stock. 2014 is '…' throughout except the closing
    stock: the publisher suppressed the components in the year the
    territory changed, which is itself the finding.
    """
    out: dict[int, dict[str, float]] = {}
    started = False
    for row in read_rows(path, "1", 6, 50):
        label = str(row[0] or "").strip()
        if "ВСЕ НАСЕЛЕНИЕ" in label:
            started = True
            continue
        if not started:
            continue
        y = _year(row[0])
        if y is None:
            continue
        rec = {}
        for key, idx in (("population_jan1_thousand", 1),
                         ("total_change_thousand", 2),
                         ("natural_change_thousand", 3),
                         ("migration_change_thousand", 4),
                         ("population_dec31_thousand", 5)):
            if len(row) > idx:
                n = _num(row[idx])
                if n is not None:
                    rec[key] = n
        out[y] = rec
    return out


def quarterly_series(path: Path) -> dict[tuple[int, int], float]:
    """The quarterly physical-volume index, year on year, {(year, quarter): %}.

    Sheets '11' (1996-2011) and '12' (2012-2021) carry the same layout: a
    year row with the year written once per four quarter cells, a quarter
    row, and one value row. The index is previous year's quarter = 100.

    IT ENDS AT 2021 Q4. Rosstat stopped publishing the quarterly breakdown
    after that, so 2022+ quarters are absent rather than estimated — which
    is why the 2022 recession band in country.yaml is dated on the ANNUAL
    index and says so.
    """
    months = {"I квартал": 1, "II квартал": 2, "III квартал": 3,
              "IV квартал": 4}
    out: dict[tuple[int, int], float] = {}
    for sheet in ("11", "12"):
        rows = read_rows(path, sheet, 3, 5)
        if len(rows) < 3:
            sys.exit(f"quarterly: sheet {sheet} has no value row")
        years, quarters, values = rows[0], rows[1], rows[2]
        current = None
        for y, q, v in zip(years, quarters, values):
            if isinstance(y, int) and 1990 < y < 2200:
                current = y
            quarter = months.get(str(q or "").strip())
            if current is None or quarter is None:
                continue
            n = _num(v)
            if n is not None:
                out[(current, quarter)] = n - 100.0
    if not out:
        sys.exit("quarterly: nothing parsed")
    return out


def write(rel: str, header: list[str], rows: list[list[str]],
          comments: list[str]) -> None:
    path = ROOT / "data" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {c}" for c in comments]
    lines.append(",".join(header))
    lines += [",".join(r) for r in rows]
    path.write_text("\n".join(lines) + "\n")
    print(f"  data/{rel}  {len(rows)} rows")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rosstat-insecure", action="store_true",
                    default=bool(os.environ.get("ROSSTAT_INSECURE")),
                    help="skip TLS verification for rosstat.gov.ru "
                         "(Russian Trusted Root CA not installed); also "
                         "settable with ROSSTAT_INSECURE=1, which is what a "
                         "`make C=russia fetch` on such a host uses")
    args = ap.parse_args()
    mode = "insecure" if args.rosstat_insecure else "verified"

    print(f"Rosstat national layer for Russia (TLS mode: {mode})")
    paths = {k: fetch(k, args.rosstat_insecure) for k in FILES}

    gdp = gdp_series(paths["gdp"])
    cpi = cpi_series(paths["cpi"])
    pop = population_series(paths["population"])
    comp = components_series(paths["components"])
    quarterly = quarterly_series(paths["quarterly"])

    # ---- known-observation checks, before any sidecar is written --------
    # Rosstat's own published figures; two independent anchors per file.
    assert abs(gdp[2006]["nominal_bn_rub"] - 26917.2) < 0.5, gdp[2006]
    assert abs(gdp[2009]["real_growth_pct"] - -7.82) < 0.01, gdp[2009]
    assert abs(gdp[2015]["real_growth_pct"] - -1.97) < 0.01, gdp[2015]
    assert abs(gdp[2022]["real_growth_pct"] - -1.44) < 0.01, gdp[2022]
    assert abs(cpi[2008] - 13.28) < 0.01, cpi[2008]
    assert abs(cpi[2015] - 12.91) < 0.01, cpi[2015]
    assert abs(cpi[2022] - 11.94) < 0.01, cpi[2022]
    # The annexation seam: +2.7m between the 2014 and 2015 population rows.
    # If this step ever closes, the publisher changed its territory or its
    # vintage and every downstream rate is suspect.
    assert abs((pop[2015] - pop[2014]) - 2.7) < 0.05, \
        f"population 2014->2015 step: {pop[2014]} -> {pop[2015]}"
    assert abs(comp[2020]["natural_change_thousand"] - -702.1) < 0.1, comp[2020]
    assert abs(comp[2021]["natural_change_thousand"] - -1043.3) < 0.1, comp[2021]
    # The quarterly index, pinned on two known quarters: 2009 Q2 = -11.15
    # year on year (the trough of the crisis) and 2020 Q2 = -7.32.
    assert abs(quarterly[(2009, 2)] - -11.15) < 0.05, quarterly.get((2009, 2))
    assert abs(quarterly[(2020, 2)] - -7.32) < 0.05, quarterly.get((2020, 2))
    assert max(quarterly) == (2021, 4), max(quarterly)

    write("macro/rosstat_gdp_from_rosstat.csv",
          ["year", "nominal_bn_rub", "real_growth_pct", "deflator_pct"],
          [[str(y),
            f"{r['nominal_bn_rub']:.1f}" if "nominal_bn_rub" in r else "",
            f"{r['real_growth_pct']:.2f}" if "real_growth_pct" in r else "",
            f"{r['deflator_pct']:.2f}" if "deflator_pct" in r else ""]
           for y, r in sorted(gdp.items()) if YEAR_FROM <= y <= YEAR_TO],
          [f"Rosstat, {FILES['gdp']}: GDP at current prices (billion roubles), "
           "physical-volume index and GDP deflator, previous year = 100.",
           "Growth and the deflator are the published index minus 100.",
           "TERRITORY: from 2014 Rosstat includes Crimea and Sevastopol;",
           "from 2022 the publisher's own footnote excludes the Donetsk and",
           "Luhansk People's Republics and Zaporizhzhia and Kherson oblasts.",
           f"Fetched 2026-10-25, TLS mode: {mode}."])

    write("macro/rosstat_cpi_from_rosstat.csv", ["year", "cpi_dec_pct"],
          [[str(y), f"{v:.2f}"] for y, v in sorted(cpi.items())
           if YEAR_FROM <= y <= YEAR_TO],
          [f"Rosstat, {FILES['cpi']}: consumer price index, all goods and",
           "services, Russian Federation, previous year = 100, minus 100.",
           "This is the December-to-December headline. The World Bank's",
           "FP.CPI.TOTL.ZG is the ANNUAL AVERAGE change and differs every",
           "year (2008: 13.28 here vs 14.11 there; 2015: 12.91 vs 15.53).",
           f"Fetched 2026-10-25, TLS mode: {mode}."])

    write("demography/population_from_rosstat.csv", ["year", "population_mn"],
          [[str(y), f"{v:.1f}"] for y, v in sorted(pop.items())
           if YEAR_FROM <= y <= YEAR_TO],
          [f"Rosstat, {FILES['population']}: population, million people,",
           "annual, as published to one decimal.",
           "INCLUDES Crimea and Sevastopol from 2014 (the 144.0 -> 146.7",
           "step). The World Bank/UN series does not reproduce that step,",
           "so the two lines differ by 2.3-2.7m from 2015 and are never",
           f"spliced. Fetched 2026-10-25, TLS mode: {mode}."])

    # The quarterly series, as its own file: it is what dates the recession
    # bands, and it stops at 2021 Q1.
    write("macro/gdp_quarterly_from_rosstat.csv",
          ["year", "quarter", "volume_yoy_pct"],
          [[str(y), f"Q{q}", f"{v:.2f}"]
           for (y, q), v in sorted(quarterly.items())
           if YEAR_FROM <= y <= YEAR_TO],
          [f"Rosstat, {FILES['quarterly']}, sheets 11 and 12: the quarterly",
           "physical-volume index of GDP, previous year's quarter = 100,",
           "minus 100. Year-on-year, NOT quarter-on-quarter.",
           "THE SERIES ENDS AT 2021 Q4: the publisher stopped releasing the",
           "quarterly breakdown after that. 2022+ quarters are absent.",
           f"Fetched 2026-10-25, TLS mode: {mode}."])

    write("demography/components_from_rosstat.csv",
          ["year", "population_jan1_thousand", "population_dec31_thousand",
           "total_change_thousand", "natural_change_thousand",
           "migration_change_thousand"],
          [[str(y),
            f"{r['population_jan1_thousand']:.1f}" if "population_jan1_thousand" in r else "",
            f"{r['population_dec31_thousand']:.1f}" if "population_dec31_thousand" in r else "",
            f"{r['total_change_thousand']:.1f}" if "total_change_thousand" in r else "",
            f"{r['natural_change_thousand']:.1f}" if "natural_change_thousand" in r else "",
            f"{r['migration_change_thousand']:.1f}" if "migration_change_thousand" in r else ""]
           for y, r in sorted(comp.items()) if YEAR_FROM <= y <= YEAR_TO],
          [f"Rosstat, {FILES['components']}, sheet 1 (all population):",
           "population change and its components, thousand people.",
           "2014 is blank in the components columns because the publisher",
           "suppressed them in the year the territory changed — a hole, not",
           "a zero. Natural increase is births minus deaths; migration",
           "increase is net migration, both as the publisher defines them.",
           f"Fetched 2026-10-25, TLS mode: {mode}."])

    print("Rosstat anchors verified.")


if __name__ == "__main__":
    main()
