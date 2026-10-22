#!/usr/bin/env python3
"""Refresh Swiss foreign-trade sidecars from the BAZG (FOCBS) open data.

Usage:  python3 -I countries/switzerland/fetch/fetch_bazg.py

The Federal Office for Customs and Border Security publishes its open-data
reports as files in a public S3 bucket behind ocean.bazg.admin.ch. The
bucket LISTING is the index: file keys carry a version suffix
(`…_en_v1/…_en_v1.csv`), so each key is resolved from the listing (highest
version, exact name pattern) rather than hardcoded. Files are SEMICOLON-
separated, UTF-8, served as application/octet-stream; quoted text fields
escape inner quotes with a BACKSLASH (\\"), not by doubling.

SCOPE. Every figure is the SWISS–LIECHTENSTEIN CUSTOMS AREA, not
Switzerland alone. It never shares a line with a Switzerland-only series.

  SA_COUNTRY_EXP / SA_COUNTRY_IMP   exports / imports by partner, monthly,
      1995-01 onward, CHF. These are "Total 1" (konjunkturelles Total):
      EXCLUDING gold bars and other precious metals, gems, art and
      antiques. THE PERIOD COLUMN MIXES MONTHS (1–12) AND QUARTERS (24–27):
      summing a year over all rows doubles it. Only months 1–12 are read,
      and the fetcher asserts the quarters equal the sum of their months
      before throwing them away. There is no World row: Total 1 is the sum
      of the six continents (Middle East is a sub-aggregate of Asia and is
      not added), cross-checked against the SNB balance of payments.

  CTCI5_EXP / CTCI5_IMP   trade by SITC rev.4 5-digit code × partner,
      monthly, 1988 onward, CHF — the GENERAL total ("Total 2",
      Generaltotal) INCLUDING gold. 4–5 GB each, so they are STREAMED and
      only the monthly aggregates are cached (bazg_<file>_monthly.csv),
      keyed to the object's ETag so a republished file is re-read. Non-
      monetary gold is SITC 971.

  TN8_controlCode_Gold_IMP   imports of tariff 7108.12 (unwrought non-
      monetary gold) by month × control code (mined / refining / other) ×
      country of origin, 2021 onward, kg and CHF.

Totals with and without gold are separate, named lines (Swiss trap 2):
gold was CHF 149.6bn of 461.0bn goods receipts in the 2025 balance of
payments. They are never summed into, spliced with, or substituted for one
another.

The PARTIAL YEAR: annual sums are written only for years with all twelve
months present; the running year is left out entirely (a year in progress
is not a small year). Its month count is printed when the fetcher runs.

Outputs:
  data/trade/goods_by_partner_from_bazg.csv
  data/trade/gold_from_bazg.csv
"""
from __future__ import annotations

import csv
import io
import re
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "trade"
CACHE = ROOT / "cache"

BUCKET = "https://ocean.bazg.admin.ch/"
HEADERS = {"User-Agent": "worldreports-data-fetcher/1.0"}
csv.field_size_limit(10 ** 8)

CONTINENTS = {"100800": "Europe", "100810": "Africa", "100820": "Asia",
              "100844": "North America", "100857": "Central and South America",
              "100870": "Oceania"}
QUARTERS = {24: (1, 2, 3), 25: (4, 5, 6), 26: (7, 8, 9), 27: (10, 11, 12)}


# ---------------------------------------------------------------- transport

def get(url: str, timeout: int = 120) -> bytes:
    last: Exception | None = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
            time.sleep(1)
            return body
        except urllib.error.HTTPError as e:
            last = e
            if e.code not in (403, 429) and e.code < 500:
                break
            time.sleep(15 * (attempt + 1))
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"{url}: {last}")


def listing() -> dict[str, tuple[str, int]]:
    """{key: (etag, size)} for every object in the bucket (the index)."""
    keys: dict[str, tuple[str, int]] = {}
    token = None
    while True:
        url = BUCKET + "?list-type=2"
        if token:
            url += "&continuation-token=" + urllib.request.quote(token, safe="")
        xml = get(url).decode("utf-8")
        if "<ListBucketResult" not in xml:
            raise RuntimeError("BAZG bucket listing: unexpected payload")
        for m in re.finditer(r"<Contents><Key>([^<]+)</Key>.*?<ETag>([^<]+)"
                             r"</ETag>.*?<Size>(\d+)</Size>", xml):
            keys[m.group(1)] = (m.group(2).replace("&quot;", "").strip('"'),
                                int(m.group(3)))
        t = re.search(r"<NextContinuationToken>([^<]+)<", xml)
        if "<IsTruncated>true" not in xml or not t:
            return keys
        token = t.group(1)


def resolve(keys: dict[str, tuple[str, int]], stem: str) -> tuple[str, str]:
    """Highest-version `open-data-reports/<stem>_vN/<stem>_vN.csv` key."""
    pat = re.compile(rf"open-data-reports/{re.escape(stem)}_v(\d+)/"
                     rf"{re.escape(stem)}_v\1\.csv")
    hits = [(int(m.group(1)), k) for k in keys if (m := pat.fullmatch(k))]
    if not hits:
        raise RuntimeError(f"BAZG listing has no {stem}_vN file")
    _, key = max(hits)
    return key, keys[key][0]


def reader(text_stream) -> csv.reader:
    return csv.reader(text_stream, delimiter=";", quotechar='"',
                      escapechar="\\", doublequote=False)


def cached_small(keys, stem: str, must_have: list[str]) -> list[dict]:
    """Download (or reuse) a small file; shape-check header before caching."""
    key, etag = resolve(keys, stem)
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / f"bazg_{Path(key).stem}_{etag[:12]}.csv"
    if not cache_file.exists():
        body = get(BUCKET + key, timeout=300)
        head = body[:4000].decode("utf-8-sig", errors="replace").splitlines()[0]
        missing = [c for c in must_have if c not in head.split(";")]
        if missing or body.count(b"\n") < 100:
            raise RuntimeError(f"{stem}: bad shape (missing {missing})")
        for old in CACHE.glob(f"bazg_{Path(key).stem}_*.csv"):
            old.unlink()
        cache_file.write_bytes(body)
    with cache_file.open(encoding="utf-8-sig", newline="") as f:
        rows = reader(f)
        header = next(rows)
        return [dict(zip(header, r)) for r in rows]


def streamed_totals(keys, stem: str) -> dict[tuple[int, int], tuple[float, float]]:
    """{(year, month): (general total CHF, SITC 971 gold CHF)} for a CTCI5
    file. The multi-GB file is streamed once and never stored; only the
    monthly aggregate is cached, under the object's ETag."""
    key, etag = resolve(keys, stem)
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / f"bazg_{Path(key).stem}_{etag[:12]}_monthly.csv"
    if not cache_file.exists():
        print(f"  streaming {key} ({keys[key][1] / 1e9:.1f} GB)…")
        agg: dict[tuple[int, int], list[float]] = defaultdict(lambda: [0.0, 0.0])
        last: Exception | None = None
        for attempt in range(3):
            agg.clear()
            try:
                req = urllib.request.Request(BUCKET + key, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=300) as r:
                    rows = reader(io.TextIOWrapper(r, encoding="utf-8-sig",
                                                   newline=""))
                    header = next(rows)
                    need = ["year", "month", "CTCI5", "Value_CHF"]
                    if any(c not in header for c in need):
                        raise RuntimeError(f"{stem}: bad header {header[:8]}")
                    iy, im, ic, iv = (header.index(c) for c in need)
                    n = 0
                    for row in rows:
                        cell = agg[(int(row[iy]), int(row[im]))]
                        v = float(row[iv]) if row[iv] else 0.0
                        cell[0] += v
                        if row[ic].startswith("971"):
                            cell[1] += v
                        n += 1
                if n < 1_000_000:
                    raise RuntimeError(f"{stem}: only {n} rows — truncated?")
                break
            except Exception as e:  # noqa: BLE001
                last = e
                print(f"  {stem} attempt {attempt + 1}: {e}", file=sys.stderr)
                time.sleep(30 * (attempt + 1))
        else:
            raise RuntimeError(f"{stem}: {last}")
        for old in CACHE.glob(f"bazg_{Path(key).stem}_*_monthly.csv"):
            old.unlink()
        lines = ["year,month,total_chf,gold_sitc971_chf"]
        lines += [f"{y},{m},{t:.0f},{g:.0f}" for (y, m), (t, g) in sorted(agg.items())]
        cache_file.write_text("\n".join(lines) + "\n")
    out = {}
    with cache_file.open() as f:
        for row in csv.DictReader(f):
            out[(int(row["year"]), int(row["month"]))] = (
                float(row["total_chf"]), float(row["gold_sitc971_chf"]))
    return out


# ---------------------------------------------------------------- checks

def check(ok: bool, msg: str) -> None:
    if not ok:
        raise RuntimeError(f"spot check failed: {msg}")


def near(got: float | None, want_bn: float, tol_bn: float = 0.05) -> bool:
    return got is not None and abs(got / 1e9 - want_bn) <= tol_bn


# ---------------------------------------------------------------- partners

SA_COLS = ["Traffic_direction", "country", "Country_txt", "year", "period",
           "Nominal_Value", "status"]


def sa_monthly(rows: list[dict], direction: str):
    """{(code, year, month): CHF} from months 1–12 only, plus names.

    Before discarding the quarter rows (24–27) each is checked against the
    sum of its three months: proof that the column really double-counts
    and that nothing else hides in it."""
    months: dict[tuple[str, int, int], float] = {}
    quarters: dict[tuple[str, int, int], float] = {}
    names: dict[str, str] = {}
    status: dict[int, set] = defaultdict(set)
    for r in rows:
        if r["Traffic_direction"] != direction:
            raise RuntimeError(f"SA_COUNTRY: direction {r['Traffic_direction']}")
        p, y = int(r["period"]), int(r["year"])
        if r["Nominal_Value"] == "":
            continue                      # a hole stays a hole
        v = float(r["Nominal_Value"])
        names[r["country"]] = r["Country_txt"]
        if 1 <= p <= 12:
            months[(r["country"], y, p)] = v
            status[y].add(r["status"])
        elif p in QUARTERS:
            quarters[(r["country"], y, p)] = v
        else:
            raise RuntimeError(f"SA_COUNTRY: unknown period code {p}")
    checked = 0
    for (c, y, q), v in quarters.items():
        parts = [months.get((c, y, m)) for m in QUARTERS[q]]
        if None in parts:
            continue
        check(abs(sum(parts) - v) <= 5, f"quarter {q} {c} {y} != its months")
        checked += 1
    check(checked > 1000, "too few quarter rows to verify the period column")
    return months, names, status


def annual(months: dict, code: str, year: int) -> float | None:
    vals = [months.get((code, year, m)) for m in range(1, 13)]
    return None if None in vals else sum(vals)


def write_partners(keys) -> None:
    exp_rows = cached_small(keys, "SA_COUNTRY_EXP_en", SA_COLS)
    imp_rows = cached_small(keys, "SA_COUNTRY_IMP_en", SA_COLS)
    exp, names, st_e = sa_monthly(exp_rows, "E")
    imp, names_i, _ = sa_monthly(imp_rows, "I")
    names.update(names_i)
    years = sorted({y for (_, y, _) in exp})
    full = [y for y in years
            if all(annual(exp, c, y) is not None for c in CONTINENTS)
            and all(annual(imp, c, y) is not None for c in CONTINENTS)]
    partial = [y for y in years if y not in full]

    t2_exp = streamed_totals(keys, "CTCI5_EXP_en")
    t2_imp = streamed_totals(keys, "CTCI5_IMP_en")

    def t2(src, y, idx):
        vals = [src.get((y, m)) for m in range(1, 13)]
        return None if None in vals else sum(v[idx] for v in vals)

    rows = []   # (year, code, name, exports, imports)
    for y in full:
        for code in sorted(names, key=lambda c: (len(c) < 6, int(c))):
            rows.append((y, code, names[code], annual(exp, code, y),
                         annual(imp, code, y)))
        t1e = sum(annual(exp, c, y) for c in CONTINENTS)
        t1i = sum(annual(imp, c, y) for c in CONTINENTS)
        rows.append((y, "TOTAL1", "Total 1 excl. gold etc. (sum of continents)",
                     t1e, t1i))
        code2 = "TOTAL2" if y >= 2012 else "TOTAL2_PRE2012"
        rows.append((y, code2, "Total 2 incl. gold (general total, SITC file)"
                     if y >= 2012 else
                     "Total 2, pre-2012 basis (gold bars largely outside)",
                     t2(t2_exp, y, 0), t2(t2_imp, y, 0)))
        rows.append((y, "GOLD_SITC971", "Non-monetary gold (SITC 971)",
                     t2(t2_exp, y, 1), t2(t2_imp, y, 1)))

    by = {(y, c): (e, i) for y, c, _, e, i in rows}
    # Spot values recorded by DISCOVERY.md (2025 exports, months only).
    for code, want in (("100800", 160.0), ("100302", 147.0), ("100844", 58.3),
                       ("111", 43.0), ("373", 15.2)):
        check(near(by[(2025, code)][0], want), f"2025 exports {code} {want}bn")
    # Second source, SNB balance of payments (bopcurra DAT1): goods foreign
    # trade receipts 2024 Total 1 283.0bn and all-in 393.8bn; 2025 461.0bn.
    check(near(by[(2024, "TOTAL1")][0], 283.0), "Total 1 exports 2024 vs SNB 283.0")
    check(near(by[(2024, "TOTAL2")][0], 393.8), "Total 2 exports 2024 vs SNB 393.8")
    check(near(by[(2025, "TOTAL2")][0], 461.0), "Total 2 exports 2025 vs SNB 461.0")
    for y in full:
        if y >= 2012:
            e1, i1 = by[(y, "TOTAL1")]
            e2, i2 = by[(y, "TOTAL2")]
            check(e2 > e1 and i2 > i1, f"{y}: Total 2 not above Total 1")
    check(near(by[(2025, "GOLD_SITC971")][0], 163.8, 0.5), "gold exports 2025")

    DATA.mkdir(parents=True, exist_ok=True)
    out = [
        "# BAZG open data, Swiss–Liechtenstein CUSTOMS AREA (not Switzerland alone).",
        "# Units: CHF mn, nominal, calendar years; annual = sum of months 1–12 of",
        "# SA_COUNTRY_EXP/IMP (quarter rows 24–27 dropped after checking they equal",
        "# their months). Partner rows are Total 1 (konjunkturelles Total): EXCLUDING",
        "# gold bars, other precious metals, gems, art and antiques. Continents and",
        "# EU/Eurozone/Middle East are aggregates; Middle East is part of Asia.",
        "# Named total lines, never one series: TOTAL1 = sum of the six continents",
        "# (= SNB BoP Total 1); TOTAL2 = general total incl. gold from CTCI5 (SITC)",
        "# files, 2012+; TOTAL2_PRE2012 = same file before 1 Jan 2012, when gold bars",
        "# entered special trade — a BREAK, not comparable with TOTAL2. GOLD_SITC971",
        "# is non-monetary gold. Blank = no data (e.g. Belgium before 1999).",
        f"# Only complete years; the running year ({', '.join(map(str, partial))}) is omitted.",
        "year,partner_code,partner,exports_chf_mn,imports_chf_mn",
    ]

    def fmt(v):
        return "" if v is None else f"{v / 1e6:.1f}"

    for y, code, name, e, i in rows:
        out.append(f"{y},{code},\"{name}\",{fmt(e)},{fmt(i)}")
    (DATA / "goods_by_partner_from_bazg.csv").write_text("\n".join(out) + "\n")
    months_partial = {y: len({m for (c, yy, m) in exp if yy == y and c == "100800"})
                      for y in partial}
    print(f"  data/trade/goods_by_partner_from_bazg.csv  {len(rows)} rows  "
          f"{full[0]}–{full[-1]}  (omitted partial: {months_partial} months; "
          f"statuses {sorted(st_e[full[-1]])} in {full[-1]})")


# ---------------------------------------------------------------- gold

GOLD_COLS = ["Traffic_direction", "year", "month", "Tariffnumber8",
             "Control_code", "Control_code_txt", "Country_isoAlpha2",
             "Country_txt", "Quantity_kg", "Value_CHF", "status"]


def write_gold(keys) -> None:
    rows = cached_small(keys, "TN8_controlCode_Gold_IMP_en", GOLD_COLS)
    by_year: dict[int, float] = defaultdict(float)
    months: dict[int, set] = defaultdict(set)
    out_rows = []
    for r in rows:
        if r["Traffic_direction"] != "I" or not r["Tariffnumber8"].startswith("7108"):
            raise RuntimeError(f"gold file: unexpected row {r['Tariffnumber8']}")
        y, m = int(r["year"]), int(r["month"])
        v = float(r["Value_CHF"])
        by_year[y] += v
        months[y].add(m)
        out_rows.append((y, m, r["status"], r["Tariffnumber8"], r["Control_code"],
                         r["Control_code_txt"], r["Country_isoAlpha2"],
                         r["Country_txt"], float(r["Quantity_kg"]), v))
    # Second source: SNB BoP non-monetary gold EXPENSES 2025 = 173.7bn.
    check(near(by_year.get(2025), 173.7, 0.1), f"gold imports 2025 {by_year.get(2025)}")
    check(min(by_year) == 2021, f"gold file starts {min(by_year)}, not 2021")
    out_rows.sort(key=lambda t: (t[0], t[1], t[4], -t[9]))
    seen = {(t[0], t[1], t[4], t[6]) for t in out_rows}
    check(len(seen) == len(out_rows), "gold file: a (month, control code, "
          "country) cell appears twice")
    partial = [y for y, ms in months.items() if len(ms) < 12]
    out = [
        "# BAZG TN8_controlCode_Gold_IMP: IMPORTS of tariff 7108.12 (unwrought non-",
        "# monetary gold) into the Swiss–Liechtenstein customs area, by month ×",
        "# control code (911 mined, 912 >=99.5% for refining, 913 >=99.5% other uses,",
        "# 914 <99.5%) × country of origin. Units: kg and CHF mn, nominal.",
        "# Gold sits in Total 2 only, never in Total 1. status prov = provisional.",
        "# month = YYYY-MM (the calendar month; part of the row key).",
        f"# Partial year(s): {', '.join(f'{y} ({len(months[y])} of 12 months)' for y in partial) or 'none'}"
        " — not an annual total.",
        "year,month,status,tariff,control_code,control_code_txt,country_iso2,country,quantity_kg,value_chf_mn",
    ]
    for y, m, st, tn, cc, cct, iso, cn, kg, v in out_rows:
        out.append(f"{y},{y}-{m:02d},{st},{tn},{cc},\"{cct.replace(chr(34), chr(39))}\","
                   f"{iso},\"{cn}\",{kg:.1f},{v / 1e6:.3f}")
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "gold_from_bazg.csv").write_text("\n".join(out) + "\n")
    print(f"  data/trade/gold_from_bazg.csv  {len(out_rows)} rows  "
          f"{min(by_year)}-01–{max(by_year)}-{max(months[max(by_year)]):02d}  "
          f"(2025 total CHF {by_year[2025] / 1e9:.1f}bn)")


def main() -> None:
    print("BAZG foreign-trade open data (Swiss–Liechtenstein customs area)")
    keys = listing()
    write_gold(keys)
    write_partners(keys)
    print("Done. Spot checks passed. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
