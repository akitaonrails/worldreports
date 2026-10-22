#!/usr/bin/env python3
"""Refresh the police-recorded 殺人 series from the National Police Agency.

Usage:  python3 -I countries/japan/fetch/fetch_npa.py

The NPA publishes one 犯罪統計資料 (crime statistics) edition per year,
linked from its year index (npa.go.jp/publications/statistics/sousa/
statistics.html) → one page per year → one e-Stat listing. The confirmed
(確定値) edition for 2020 onward is a CSV (cp932); 2008–2019 are PDFs only
(the 2008–2012 and 2017–2018 editions as corrected 訂正版 reissues); 2006
is a PDF on npa.go.jp itself. Nothing is hardcoded: the fetcher walks the
index, resolves each listing, and takes table 1 (刑法犯 罪種別 認知・検挙
件数・検挙人員 対前年比較), row 殺人.

Things this source will mislead you about.

**殺人 is not homicide deaths.** The Japanese police category 殺人
INCLUDES ATTEMPTS AND PREPARATION (未遂・予備) and is counted per
recorded offence, at the place of occurrence. In 2025 it was 976, against
211 deaths certified as homicide (他殺) by MHLW vital statistics. Both are
correct; they measure different things and are two lines, never one and
never spliced (SOURCING §4). The column name says so.

**Each edition carries two years.** Table 1 compares the year with the
previous one, so almost every year is published twice. The value for a
year is taken from the NEWER edition (its previous-year column) where one
exists, because the NPA reissues corrections that way; every disagreement
between the two is printed. 2007 has no reachable own edition (its e-Stat
listing is empty) and comes only from the 2008 edition.

**The PDF is parsed, so the parse proves itself.** Table 1 prints
current, previous and their difference: a row is accepted only when
current − previous equals the printed difference, for both recorded and
cleared offences.

Outputs are `_from_npa` sidecars. Nothing here overwrites a curated file.
"""
from __future__ import annotations

import csv
import html
import io
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    raise SystemExit(
        "pdfplumber is required for the 2006-2019 PDF editions (pip "
        "install -r requirements-fetch.txt). Refusing to skip them."
    )

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "security"
CACHE = ROOT / "cache"

Y0, Y1 = 2006, 2025
INDEX = "https://www.npa.go.jp/publications/statistics/sousa/statistics.html"
ESTAT_FILE = ("https://www.e-stat.go.jp/stat-search/file-download"
              "?statInfId={id}&fileKind={kind}")

# Second publisher, same idea: MHLW vital statistics, deaths certified as
# homicide (他殺, cause 20300), Japanese nationals in Japan, 2025 final
# (DISCOVERY.md). Police 殺人 includes attempts, so it must sit several
# times above this; a ratio outside 3–7 means the wrong row was read.
MHLW_HOMICIDE_DEATHS_2025 = 211

_last_request = 0.0


def norm(s) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(s or "")))


def get(url: str, check, cache_file: Path | None = None) -> bytes:
    """One payload, shape-checked BEFORE caching, polite, with backoff."""
    global _last_request
    if cache_file is not None and cache_file.exists():
        return cache_file.read_bytes()
    last = None
    for attempt in range(5):
        wait = 1.5 - (time.time() - _last_request)
        if wait > 0:
            time.sleep(wait)
        try:
            _last_request = time.time()
            req = urllib.request.Request(
                url, headers={"User-Agent": "worldreports-fetch"})
            with urllib.request.urlopen(req, timeout=180) as r:
                blob = r.read()
            check(blob)
            if cache_file is not None:
                CACHE.mkdir(exist_ok=True)
                cache_file.write_bytes(blob)
            return blob
        except urllib.error.HTTPError as e:
            last = e
            time.sleep(30 * (attempt + 1) if e.code in (403, 429)
                       else 3 * (attempt + 1))
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"{url}: {last}")


def is_html(blob: bytes) -> None:
    if b"<html" not in blob[:5000].lower():
        raise ValueError("not an HTML page")


def is_pdf(blob: bytes) -> None:
    if not blob.startswith(b"%PDF"):
        raise ValueError("payload is not a PDF (error page?)")


def is_csv(blob: bytes) -> None:
    head = blob[:300].decode("cp932", "replace").lstrip()
    if not head.startswith("第１表") or "罪種別" not in head:
        raise ValueError("CSV does not open with table 1 (error page?)")


def decode(blob: bytes) -> str:
    for enc in ("utf-8", "cp932"):
        try:
            return blob.decode(enc)
        except UnicodeDecodeError:
            continue
    return blob.decode("cp932", "replace")


def links(url: str) -> list[tuple[str, str]]:
    t = decode(get(url, is_html))
    return [(urllib.parse.urljoin(url, html.unescape(h)),
             norm(re.sub(r"<[^>]+>", "", lab)))
            for h, lab in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
                                     t, re.S | re.I)]


def edition_year(label: str) -> int | None:
    """'犯罪統計資料(令和7年1~12月分【確定値】)' → 2025; partial years → None."""
    if "確定" not in label or not re.search(r"1~12月|1月~令和元年12月",
                                            label):
        return None
    if "令和元年12月" in label:
        return 2019
    m = re.search(r"(平成|令和)(\d{1,2})年", label)
    if not m:
        return None
    return {"平成": 1988, "令和": 2018}[m.group(1)] + int(m.group(2))


def estat_listing(url: str) -> tuple[str, list[str]] | None:
    """Old SG1 (bid=) and new (lid=) listing links → (statInfId, kinds)."""
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    if "bid" in q:
        key, url = (f"tclass{q['bid'][0]}",
                    "https://www.e-stat.go.jp/stat-search/files?page=1"
                    f"&layout=datalist&tclass={q['bid'][0]}&cycle=0")
    elif "lid" in q:
        key = f"lid{q['lid'][0]}"
    else:
        return None
    blob = get(url, is_html, CACHE / f"npa_list_{key}.html").decode("utf-8")
    items = blob.split('stat-dataset_list-item"')[1:]
    found = []
    for blk in items:
        # The item's own title is the text before 調査年月; what follows
        # it in the block is page chrome.
        title = norm(html.unescape(re.sub(r"<[^>]+>", " ", blk)))
        title = title.split("調査年月")[0]
        if "犯罪統計" not in title or "について" in title:
            continue
        ids = sorted(set(re.findall(r"statInfId=(\d{12})", blk)))
        kinds = sorted(set(re.findall(r"fileKind=(\d)", blk)))
        if len(ids) == 1:
            found.append((ids[0], kinds))
    if len(found) > 1:
        raise RuntimeError(f"{url}: {len(found)} candidate editions")
    return found[0] if found else None


# ------------------------------------------------------------- table 1

def parse_csv(blob: bytes, year: int) -> dict[int, dict]:
    rows = list(csv.reader(io.StringIO(blob.decode("cp932"))))
    end = next(i for i, r in enumerate(rows) if i and r and
               norm(r[0]).startswith("第2表"))
    t1 = rows[:end]
    groups = next(r for r in t1 if "認知件数" in [norm(x) for x in r])
    groups = [norm(x) for x in groups]
    years = next(r for r in t1 if any(re.match(r"\d{4}年", norm(x))
                                      for x in r))
    col = {}
    for g in ("認知件数", "検挙件数", "検挙人員"):
        i = groups.index(g)
        cur, prev = norm(years[i]), norm(years[i + 1])
        if not (cur.startswith(f"{year}年") and
                prev.startswith(f"{year - 1}年")):
            raise RuntimeError(f"CSV {year}: {g} columns are {cur}/{prev}")
        col[g] = i
    hit = [r for r in t1 if len(r) > 1 and norm(r[1]) == "殺人"]
    if len(hit) != 1:
        raise RuntimeError(f"CSV {year}: {len(hit)} 殺人 rows in table 1")
    r = hit[0]
    def n(c):  # a zero difference may be printed as "-"
        v = norm(r[c]).replace(",", "")
        return 0 if v == "-" else int(v)
    for g in ("認知件数", "検挙件数"):
        if n(col[g]) - n(col[g] + 1) != n(col[g] + 2):
            raise SystemExit(f"  !! CSV {year} 殺人 {g}: difference does "
                             f"not reconcile")
    return {y: {"recorded": n(col["認知件数"] + k),
                "cleared": n(col["検挙件数"] + k),
                "persons": n(col["検挙人員"] + k)}
            for k, y in ((0, year), (1, year - 1))}


# A zero difference is printed as "-".
NUM = r"(-?[\d,]+(?:\.\d+)?|-)"


def parse_pdf(blob: bytes, year: int) -> dict[int, dict]:
    with pdfplumber.open(io.BytesIO(blob)) as pdf:
        for page in pdf.pages[:20]:
            text = page.extract_text() or ""
            flat = norm(text)
            if "第1表刑法犯罪種別認知・検挙件数・検挙人員対前年比較" not in flat:
                continue
            if "……" in text:
                continue  # the table of contents
            for line in text.splitlines():
                m = re.match(r"\s*殺\s*人\s+" + r"\s+".join([NUM] * 15),
                             line)
                if not m:
                    continue
                v = [0.0 if x == "-" else float(x.replace(",", ""))
                     for x in m.groups()]
                rec, rec_p, rec_d = v[0:3]
                clr, clr_p, clr_d = v[4:7]
                per, per_p = v[11:13]
                if rec - rec_p != rec_d or clr - clr_p != clr_d:
                    raise SystemExit(f"  !! PDF {year} 殺人: differences do "
                                     f"not reconcile in {line!r}")
                return {year: {"recorded": int(rec), "cleared": int(clr),
                               "persons": int(per)},
                        year - 1: {"recorded": int(rec_p),
                                   "cleared": int(clr_p),
                                   "persons": int(per_p)}}
    raise RuntimeError(f"PDF {year}: table 1 殺人 row not found")


# ------------------------------------------------------------------ run

def editions() -> dict[int, tuple[str, str, Path]]:
    """{year: (url, kind, cache file)} for each confirmed annual edition."""
    out = {}
    for url, lab in links(INDEX):
        y = edition_year(lab)
        if y is None or not Y0 <= y <= Y1 or "/toukei/" not in url:
            continue
        found = None
        for href, sub in links(url):
            if href.lower().endswith(".pdf") and "/toukei/" in href:
                found = (href, "pdf", CACHE / f"npa_{y}_{Path(href).name}")
                break
            res = estat_listing(href) if "e-stat" in href else None
            if res:
                sid, kinds = res
                kind = "1" if "1" in kinds else "2" if "2" in kinds else None
                if kind is None:
                    raise RuntimeError(f"{y}: no CSV or PDF in {kinds}")
                found = (ESTAT_FILE.format(id=sid, kind=kind),
                         "csv" if kind == "1" else "pdf",
                         CACHE / f"npa_{y}_{sid}.{'csv' if kind == '1' else 'pdf'}")
                break
        if found:
            out[y] = found
        else:
            print(f"    {y}: no reachable edition on {url} — covered by the "
                  f"next edition's previous-year column")
    return out


def main() -> None:
    print("NPA — 犯罪統計資料, table 1, 殺人 (calendar year, 確定値)")
    eds = editions()
    print(f"  index: {len(eds)} confirmed editions "
          f"{min(eds)}–{max(eds)}")
    by_ed: dict[int, dict[int, dict]] = {}
    for y, (url, kind, cache) in sorted(eds.items()):
        blob = get(url, is_csv if kind == "csv" else is_pdf, cache)
        by_ed[y] = (parse_csv if kind == "csv" else parse_pdf)(blob, y)
        print(f"    {y} ({kind}): 殺人 recorded {by_ed[y][y]['recorded']:,}"
              f", previous year {by_ed[y][y - 1]['recorded']:,}")

    rows: dict[int, dict] = {}
    for ed in sorted(by_ed):          # newer editions overwrite older ones
        for y, v in by_ed[ed].items():
            if not Y0 <= y <= Y1:
                continue
            if y in rows and rows[y] != v:
                print(f"    revision {y}: {rows[y]} → {v} (edition {ed})")
            rows[y] = v
    missing = sorted(set(range(Y0, Y1 + 1)) - set(rows))
    if missing:
        raise SystemExit(f"  !! years with no edition: {missing}")

    def check(label, got, want):
        if got != want:
            raise SystemExit(f"  !! {label} = {got:,}, published {want:,}")
        print(f"  ok {label}: {got:,}")

    check("殺人 recorded 2025", rows[2025]["recorded"], 976)
    check("殺人 recorded 2024", rows[2024]["recorded"], 970)
    check("殺人 cleared 2025", rows[2025]["cleared"], 961)
    ratio = rows[2025]["recorded"] / MHLW_HOMICIDE_DEATHS_2025
    if not 3 < ratio < 7:
        raise SystemExit(f"  !! police 殺人 / MHLW homicide deaths 2025 = "
                         f"{ratio:.1f}, outside 3–7")
    print(f"  ok police 殺人 (incl. attempts) / MHLW homicide deaths 2025 = "
          f"{ratio:.1f}× — two definitions, never one line")

    path = DATA / "homicide_police_from_npa.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        fh.write("""\
# National Police Agency, 犯罪統計資料 (confirmed annual editions), table 1
# 刑法犯 罪種別 認知・検挙件数・検挙人員, row 殺人. OFFENCES recorded by the
# police, calendar year, place of occurrence, all persons in Japan.
# 殺人 INCLUDES ATTEMPTS AND PREPARATION (未遂・予備): it is NOT the number
# of people killed. MHLW counts 211 homicide deaths (他殺) in 2025 against
# 976 recorded 殺人 here — two definitions, two lines, never spliced.
# cleared = 検挙件数 (offences cleared, may include earlier years' cases);
# persons_cleared = 検挙人員. Each year from the newest edition carrying it.
""")
        w = csv.writer(fh)
        w.writerow(["year", "satsujin_recorded_incl_attempts",
                    "satsujin_cleared", "satsujin_persons_cleared"])
        for y in sorted(rows):
            r = rows[y]
            w.writerow([y, r["recorded"], r["cleared"], r["persons"]])
    print(f"  -> data/security/homicide_police_from_npa.csv  {len(rows)} rows "
          f"({min(rows)}–{max(rows)})")
    print("Done. Diff the sidecar before adopting.")


if __name__ == "__main__":
    main()
