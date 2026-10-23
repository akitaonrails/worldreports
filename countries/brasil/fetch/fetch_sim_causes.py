#!/usr/bin/env python3
"""Deaths from COVID-19, influenza and dengue, from SIM via DATASUS TabNet.

Usage:  python3 scripts/fetch_sim_causes.py

Outputs (sidecars — a person diffs them into the curated files):
  data/social/epidemic_deaths_from_sim.csv   year,covid,influenza,dengue  (2000-)
  data/social/deaths_from_sim.csv            year,registered,suicide,road  (2000-)

The second file is read off the same tables: `registered` is the table's
own Total row (every registered death of a Brazilian resident), `suicide`
sums X60-X84 (intentional self-harm) and `road` sums V01-V89, the
Ministry's "acidentes de transporte terrestre". These are certificates as
coded; the WHO's road-traffic estimate redistributes ill-defined and
unspecified deaths onto causes, so it reads two or so points higher per
100,000. Both are drawn, labelled.

Same instrument as the homicide series in fetch_violence.py: SIM death
certificates, counted by the victim's residence, classified by the
underlying cause the certifying doctor wrote. That makes these three
directly comparable to each other and to the homicide plate, which no
mix of ministry dashboards would be.

Three things this encodes, each of which silently corrupts the series if
you assume otherwise:

  - COVID is NOT under U07 here. TabNet's `obt10uf.def` carries no ICD-10
    chapter XXII at all, so a query for U07.1 returns zero rather than an
    error. Brazil files COVID deaths under B34 ("doenças por vírus, de
    localização não especificada"), whose pre-pandemic baseline is ~60
    deaths a year — 213,233 in 2020. Reading B34 as a COVID proxy is only
    honest because of that baseline, so the fetcher keeps B34's pre-2020
    values instead of zeroing them, and the plate shows them.

  - SIM is not the Ministry's COVID panel. The panel counted 194,949 for
    2020; SIM has 213,233. The panel counted notifications as they came in
    during the emergency, SIM counts death certificates as finally coded.
    They are different instruments, and the gap is not an error in either.

  - Dengue changes its ICD-10 code mid-series. The 2019 revision moved
    dengue from A90/A91 to A97, and SIM switched during 2025: A97 appears
    with 4 deaths in 2024, then carries the entire series from 2025 while
    A90/A91 disappear. Reading only the old pair reports 2025 as a year
    in which nobody died of dengue. TabNet does signal it — the A90 row
    is labelled ">> A97" — but it returns a table either way.

  - A cause absent from the table is absent, not zero: TabNet omits rows
    with no deaths, so a code that was never queried and a code with a
    genuine zero look identical. That is why the last year is written
    blank rather than 0 when a cause is missing, instead of asserting a
    number nobody measured.

2025 is included as a complete year on the evidence of its own volume:
its 1,534,588 registered deaths already exceed 2024's 1,532,015. The 2026
file exists in TabNet and is genuinely partial, so YEAR_TO stops short of
it rather than publishing a half-year as if it were a year.

TabNet speaks CGI: latin-1 encoded parameter names, one POST per year, the
table arriving inside a <PRE> block as semicolon-separated text.
"""
from __future__ import annotations

import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "sim"
DATA = ROOT / "data"
CACHE.mkdir(parents=True, exist_ok=True)

URL = "http://tabnet.datasus.gov.br/cgi/tabcgi.exe?sim/cnv/obt10uf.def"

YEAR_FROM, YEAR_TO = 2000, 2025

# ICD-10 categories summed into each column. B34 carries COVID (see above);
# influenza is the three J09-J11 categories, which distinguish the virus
# subtype rather than the disease; dengue is classic plus haemorrhagic.
CAUSES = {
    "covid": ["B34"],
    "influenza": ["J09", "J10", "J11"],
    # dengue migrated from A90/A91 to A97 in the ICD-10 2019 update, which
    # SIM adopted during 2025: A97 first appears with 4 deaths in 2024, then
    # carries the whole series from 2025 while A90/A91 vanish. Summing all
    # three is what makes the column continuous across the switch — reading
    # only A90/A91 reports 2025 as a year with no dengue deaths at all.
    "dengue": ["A90", "A91", "A97"],
}

# Summed into deaths_from_sim.csv. Ranges of ICD-10 categories, inclusive.
RANGES = {
    "suicide": ("X", 60, 84),
    "road": ("V", 1, 89),
}
TOTAL = re.compile(r'^"?Total"?;\s*(\d+)\s*$')

# TabNet prefixes some rows with a footnote marker — #, @ and & all appear,
# the last on exactly the A97 row that carries dengue from 2025 — and the
# count is the unquoted field after the quoted label.
ROW = re.compile(r'^"?[^A-Z"]*([A-Z]\d{2})\b[^"]*"?;\s*(\d+)\s*$')


def query(year: int) -> str:
    """One year's deaths by ICD-10 category, cached on disk."""
    cache_file = CACHE / f"obt10uf_{year}.txt"
    if cache_file.exists():
        return cache_file.read_text(encoding="latin-1")
    params = [
        ("Linha", "Categoria_CID-10"),
        ("Coluna", "--N\xe3o-Ativa--"),
        ("Incremento", "\xd3bitos_p/Resid\xeanc"),
        ("Arquivos", f"obtuf{year % 100:02d}.dbf"),
        ("formato", "prn"),
        ("mostre", "sim"),
    ]
    body = "&".join(
        f"{urllib.parse.quote(k, encoding='latin-1')}="
        f"{urllib.parse.quote(v, encoding='latin-1')}" for k, v in params)
    req = urllib.request.Request(
        URL, data=body.encode("latin-1"),
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "User-Agent": "brasil-reports/1.0"})
    with urllib.request.urlopen(req, timeout=180) as r:
        html = r.read().decode("latin-1")
    cache_file.write_text(html, encoding="latin-1")
    return html


def categories(html: str) -> dict[str, int]:
    """{ICD-10 category: deaths} from the <PRE> table."""
    pre = re.search(r"<PRE>(.*?)</PRE>", html, re.S | re.I)
    if not pre:
        raise ValueError("no <PRE> block — TabNet returned a page, not a table")
    out = {}
    for raw in pre.group(1).splitlines():
        hit = ROW.match(raw.strip())
        if hit:
            out[hit.group(1)] = int(hit.group(2))
    if not out:
        raise ValueError("<PRE> block parsed to no rows")
    return out


def total(html: str) -> int:
    """The table's own Total row: every registered death that year."""
    pre = re.search(r"<PRE>(.*?)</PRE>", html, re.S | re.I)
    for raw in pre.group(1).splitlines():
        hit = TOTAL.match(raw.strip())
        if hit:
            return int(hit.group(1))
    raise ValueError("no Total row in the <PRE> block")


def in_range(cats: dict[str, int], letter: str, lo: int, hi: int) -> int:
    return sum(v for k, v in cats.items()
               if k[0] == letter and lo <= int(k[1:]) <= hi)


# Spot values read off TabNet by hand on 2026-10-22; a fetch that does not
# reproduce them writes nothing.
SPOT = {2019: 1_349_801}


def main() -> None:
    print("SIM / DATASUS TabNet — deaths by ICD-10 category...")
    rows, deaths = {}, {}
    for year in range(YEAR_FROM, YEAR_TO + 1):
        html = query(year)
        cats = categories(html)
        rows[year] = {name: sum(cats.get(c, 0) for c in codes)
                      for name, codes in CAUSES.items()}
        deaths[year] = {"registered": total(html),
                        **{k: in_range(cats, *r) for k, r in RANGES.items()}}
        # the categories must add up to the Total row, or a row was missed
        if sum(cats.values()) != deaths[year]["registered"]:
            raise SystemExit(f"{year}: categories sum to {sum(cats.values())}"
                             f", the Total row says "
                             f"{deaths[year]['registered']}")
        print(f"  [{year}] " + "  ".join(
            f"{k}={v:,}" for k, v in rows[year].items()))

    lines = ["year,covid,influenza,dengue"]
    for year, vals in rows.items():
        # a zero in the last year is "not loaded yet", not "nobody died"
        cells = ["" if year == YEAR_TO and vals[c] == 0 else str(vals[c])
                 for c in ("covid", "influenza", "dengue")]
        lines.append(f"{year}," + ",".join(cells))
    for year, want in SPOT.items():
        if deaths[year]["registered"] != want:
            raise SystemExit(f"{year}: {deaths[year]['registered']} registered"
                             f" deaths, expected {want}; nothing written")
    out = DATA / "social" / "epidemic_deaths_from_sim.csv"
    out.write_text("\n".join(lines) + "\n")
    print(f"  -> {out.relative_to(ROOT)} ({YEAR_FROM}-{YEAR_TO})")

    lines = ["year,registered,suicide,road"]
    for year, d in deaths.items():
        lines.append(f"{year},{d['registered']},{d['suicide']},{d['road']}")
    out = DATA / "social" / "deaths_from_sim.csv"
    out.write_text("\n".join(lines) + "\n")
    print(f"  -> {out.relative_to(ROOT)} ({YEAR_FROM}-{YEAR_TO})")
    print("Done.")


if __name__ == "__main__":
    main()
