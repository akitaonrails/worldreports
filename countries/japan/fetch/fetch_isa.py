#!/usr/bin/env python3
"""Refresh the migration series: foreign residents, entrants, naturalisations.

Usage:  python3 -I countries/japan/fetch/fetch_isa.py

The Immigration Services Agency (出入国在留管理庁, ISA) publishes its
statistics through e-Stat's anonymous FILE layer. Its two index pages on
moj.go.jp list one e-Stat listing (lid) per period; statInfIds change with
every edition, so nothing below is hardcoded: the fetcher reads the
index, opens each period's listing, picks the table by its TITLE, and
downloads whatever file e-Stat serves today. The MOJ Civil Affairs Bureau
publishes naturalisations as one PDF linked from its statistics page.

Things this source will mislead you about.

**The stock is two regimes, and they are never one line.** In July 2012
the alien registration system (外国人登録, 登録外国人統計) was abolished
and the residence card (在留カード) began. "Registered foreigners"
(2006–2011, end-December) is a different population from "foreign
residents" (在留外国人, end-2012 onward): registration could include
short-stayers and others with no residence card. The CSV keeps them in
two sets of columns that never share a row; the 2011→2012 step is the
seam, not a fall.

**在留外国人 is not every foreigner in Japan.** It is mid- to long-term
residents (residence-card holders) plus special permanent residents. It
excludes short-term visitors, diplomats and the undocumented. The ISA's
broader 総在留外国人 (every foreign national with a status) is its own
column. The Census (3.84mn on 1 Oct 2025) is a third stock for one idea.

**Everything is citizenship.** Japan publishes no country-of-birth cut,
and a naturalisation takes somebody out of the foreign-resident stock
without anybody moving — which is why naturalisations sit beside it.
Nationality labels changed inside the residence-card era: Korea was
published as 韓国・朝鮮 and later split into 韓国 and 朝鮮, so the two
are separate columns, never joined.

**An entry is an event, not a person, and most entries are tourists.**
新規入国外国人 (new entrants: first entry, excluding re-entry permits)
in 2025 was 39.2mn, of which 38.5mn were 短期滞在 (temporary visitors).
Only the non-short-stay remainder, 726,420, is migration in any useful
sense; a chart of the headline total is a tourism chart. All entrants
(入国外国人, including residents returning on re-entry permits) is a
separate column again. 2020–2022 are the border closures.

**Naturalisation is three numbers in one year, not one cohort.**
Applications, grants and refusals in a calendar year are decisions on
different cohorts; grants are not "applications approved this year".

Every spot value below is asserted (the run fails before a sidecar is
written) against the figure DISCOVERY.md verified for the same period.

Outputs are `_from_isa` / `_from_moj` sidecars. Nothing here overwrites
a curated file.
"""
from __future__ import annotations

import csv
import html
import io
import re
import struct
import time
import unicodedata
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

try:
    import openpyxl
    import pdfplumber
except ImportError:
    raise SystemExit(
        "openpyxl and pdfplumber are required (pip install -r "
        "requirements-fetch.txt). Refusing to skip sources silently."
    )

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "migration"
CACHE = ROOT / "cache"

Y0, Y1 = 2006, 2025          # atlas window; ISA annual tables end at 2025

RESIDENTS_INDEX = ("https://www.moj.go.jp/isa/policies/statistics/"
                   "toukei_ichiran_touroku.html")
ENTRANTS_INDEX = ("https://www.moj.go.jp/isa/policies/statistics/"
                  "toukei_ichiran_nyukan.html")
NATURAL_PAGE = "https://www.moj.go.jp/MINJI/toukei_t_minj03.html"
ESTAT_LIST = ("https://www.e-stat.go.jp/stat-search/files?page=1"
              "&layout=datalist&lid={lid}")
ESTAT_FILE = ("https://www.e-stat.go.jp/stat-search/file-download"
              "?statInfId={id}&fileKind={kind}")

# Nationality columns (residence-card era only). Labels are matched after
# NFKC and whitespace removal; 韓国・朝鮮 and 韓国 are different scopes.
NATIONALITIES = {
    "中国": "residents_china", "ベトナム": "residents_vietnam",
    "韓国": "residents_korea_south",
    "韓国・朝鮮": "residents_korea_incl_north",
    "フィリピン": "residents_philippines", "ブラジル": "residents_brazil",
    "ネパール": "residents_nepal", "インドネシア": "residents_indonesia",
}

# Second-source magnitude: the 2025 Census count of foreign nationals,
# 1 October 2025 (Statistics Bureau, DISCOVERY.md "three stocks").
CENSUS_2025_FOREIGN = 3_840_000

_last_request = 0.0


# ------------------------------------------------------------ plumbing

def norm(s) -> str:
    """NFKC, all whitespace (incl. ideographic space) removed."""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(s or "")))


def get(url: str, check, cache_file: Path | None = None) -> bytes:
    """One payload, shape-checked BEFORE caching, polite and with backoff.

    `check(blob)` raises if the payload is not what was asked for (an
    HTML error page under HTTP 200 must never land in the cache).
    """
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


def is_listing(blob: bytes) -> None:
    is_html(blob)
    if b"stat-dataset_list-item" not in blob:
        raise ValueError("e-Stat listing has no dataset items")


def is_sheet(blob: bytes) -> None:
    if blob[:2] == b"PK":
        zipfile.ZipFile(io.BytesIO(blob)).testzip()
    elif blob[:8] != b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        raise ValueError("payload is neither xlsx nor xls (error page?)")


def is_pdf(blob: bytes) -> None:
    if not blob.startswith(b"%PDF"):
        raise ValueError("payload is not a PDF (error page?)")


def page_links(url: str) -> list[tuple[str, str]]:
    """(href, NFKC label) for every link on a moj.go.jp page."""
    t = get(url, is_html).decode("utf-8", "replace")
    t = unicodedata.normalize("NFKC", t)
    return [(html.unescape(h), norm(re.sub(r"<[^>]+>", "", lab)))
            for h, lab in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
                                     t, re.S)]


def section(url: str, start: str, stop: str) -> str:
    t = unicodedata.normalize(
        "NFKC", get(url, is_html).decode("utf-8", "replace"))
    i = t.find(start)
    if i < 0:
        raise RuntimeError(f"{url}: section {start!r} not found")
    j = t.find(stop, i + len(start))
    return t[i:j if j > 0 else None]


def listing(lid: str) -> list[dict]:
    """The datasets on one e-Stat listing: table number, title, ids."""
    blob = get(ESTAT_LIST.format(lid=lid), is_listing,
               CACHE / f"isa_list_{lid}.html")
    out = []
    for blk in blob.decode("utf-8").split('stat-dataset_list-item"')[1:]:
        text = [x.strip() for x in html.unescape(
            re.sub(r"<[^>]+>", "\n", blk)).split("\n") if x.strip()]
        ids = sorted(set(re.findall(r"statInfId=(\d{12})", blk)))
        kinds = sorted(set(re.findall(r"fileKind=(\d)", blk)))
        if len(ids) != 1:
            continue
        num = text[text.index("表番号") + 1] if "表番号" in text else ""
        title = text[text.index("表番号") + 2] if "表番号" in text else ""
        out.append({"num": norm(num), "title": norm(title),
                    "id": ids[0], "kinds": kinds})
    return out


def pick(datasets: list[dict], lid: str, ok) -> dict:
    hits = [d for d in datasets if ok(d["title"])]
    if len(hits) != 1:
        raise RuntimeError(f"lid {lid}: expected one table, found "
                           f"{[(d['num'], d['title']) for d in hits]}")
    return hits[0]


def workbook(d: dict) -> list[list]:
    """First worksheet of an e-Stat Excel download, as a list of rows."""
    kind = "0" if "0" in d["kinds"] else "4"
    if kind not in d["kinds"]:
        raise RuntimeError(f"{d['num']}: no Excel file ({d['kinds']})")
    blob = get(ESTAT_FILE.format(id=d["id"], kind=kind), is_sheet,
               CACHE / f"isa_{d['id']}_{kind}.bin")
    if blob[:2] == b"PK":
        ws = openpyxl.load_workbook(io.BytesIO(blob), read_only=True,
                                    data_only=True).worksheets[0]
        return [list(r) for r in ws.iter_rows(values_only=True)]
    return xls_rows(blob)


def number(v) -> int | None:
    if isinstance(v, (int, float)):
        if v != int(v):
            raise ValueError(f"non-integer count {v!r}")
        return int(v)
    s = norm(v).replace(",", "")
    if s in ("", "-", "−", "…", "x", "X", "***"):
        return None
    return int(s)


def wareki(label: str) -> int | None:
    """'平成18年' / '令和元年' / '令和7年末' → Gregorian year, else None."""
    m = re.fullmatch(r"(平成|令和)(元|\d{1,2})年.*", norm(label))
    if not m:
        return None
    n = 1 if m.group(2) == "元" else int(m.group(2))
    return {"平成": 1988, "令和": 2018}[m.group(1)] + n


assert wareki("平成１８年") == 2006 and wareki("令和元年") == 2019
assert wareki("令和7年12月末") == 2025


def check(label: str, got, want: int) -> None:
    if got != want:
        raise SystemExit(f"  !! {label} = {got!r}, published {want:,} — "
                         f"not writing")
    print(f"  ok {label}: {got:,}")


def write(name: str, header: list[str], rows: dict[int, dict],
          comment: str) -> int:
    path = DATA / name
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", newline="", encoding="utf-8") as fh:
        for line in comment.strip().splitlines():
            fh.write(f"# {line}\n")
        w = csv.writer(fh)
        w.writerow(header)
        for y in sorted(rows):
            cells = [rows[y].get(h) for h in header[1:]]
            if all(v is None for v in cells):
                continue
            w.writerow([y] + ["" if v is None else v for v in cells])
            n += 1
    span = f"{min(rows)}–{max(rows)}" if rows else "empty"
    print(f"  -> data/migration/{name}  {n} rows ({span})")
    return n


# ------------------------------------------------- wide-table helpers

def header_map(rows: list[list], first_data: int) -> dict[str, int]:
    """Column name (header rows joined, normalised) → column index."""
    # A row with a single filled cell is the table's title, not a header.
    head = [r for r in rows[:first_data]
            if sum(1 for v in r if v not in (None, "")) > 1]
    width = max(len(r) for r in head)
    names = {}
    for c in range(width):
        name = "".join(norm(r[c]) for r in head
                       if c < len(r) and r[c] is not None
                       and not isinstance(r[c], (int, float)))
        if name:
            names.setdefault(name, c)
    return names


def row_label(r: list) -> str:
    for v in r[:3]:
        if isinstance(v, str) and norm(v):
            return norm(v)
    return ""


def first_row(rows: list[list], label: str) -> int:
    for i, r in enumerate(rows):
        if row_label(r) == label and any(
                isinstance(v, (int, float)) for v in r):
            return i
    raise RuntimeError(f"no row labelled {label!r}")


# ----------------------------------------------------- foreign residents

def stock_wide(rows: list[list], card_era: bool) -> dict:
    i = first_row(rows, "総数")
    cols = header_map(rows, i)
    if "総数" not in cols:
        raise RuntimeError(f"no 総数 column in {list(cols)[:8]}")
    tot = rows[i]
    out = {"total": number(tot[cols["総数"]]),
           "permanent": number(tot[cols["永住者"]]),
           "special_permanent": number(tot[cols["特別永住者"]])}
    if card_era:
        seen = {}
        for r in rows[i + 1:]:
            lab = row_label(r)
            if lab in NATIONALITIES:
                if lab in seen:
                    raise RuntimeError(f"nationality {lab} appears twice")
                seen[lab] = number(r[cols["総数"]])
        out["nat"] = seen
    return out


def stock_long(rows: list[list]) -> dict:
    """The DB-style edition: one row per (時点, 州, 国籍・地域, 在留資格)."""
    h = next(i for i, r in enumerate(rows[:10]) if norm(r[0]) == "時点")
    head = [norm(x) for x in rows[h]]
    ci = {k: head.index(k) for k in ("州", "国籍・地域", "在留資格")}
    cv = max(i for i, x in enumerate(head) if x)
    if not head[cv].endswith("数"):
        raise RuntimeError(f"long-format value column is {head[cv]!r}")
    out = {"nat": {}}
    for r in rows[h + 1:]:
        if r[0] is None:
            continue
        reg, nat, st = (norm(r[ci["州"]]), norm(r[ci["国籍・地域"]]),
                        norm(r[ci["在留資格"]]))
        v = number(r[cv])
        if reg == nat == "総数":
            if st == "総数":
                out["total"] = v
            elif st == "永住者":
                out["permanent"] = v
            elif st == "特別永住者":
                out["special_permanent"] = v
        elif st == "総数" and nat in NATIONALITIES and reg != "総数":
            if nat in out["nat"]:
                raise RuntimeError(f"nationality {nat} appears twice")
            out["nat"][nat] = v
    return out


def stock(rows: list[list], card_era: bool) -> dict:
    if any(norm(r[0]) == "時点" for r in rows[:10] if r):
        return stock_long(rows)
    return stock_wide(rows, card_era)


def residents() -> int:
    print("ISA — 在留外国人統計 / 登録外国人統計 (stock, end-December)")
    # midashi01 = 在留外国人統計 (2012-), midashi02 = 登録外国人統計; within
    # the latter, only the 2006-2011 block (the 1959-2005 PDFs follow).
    card = section(RESIDENTS_INDEX, 'id="midashi01"', 'id="midashi02"')
    reg = section(RESIDENTS_INDEX, 'id="midashi02"', "1959年~2005年")
    if "在留外国人統計" not in card[:200] or "登録外国人統計" not in reg[:200]:
        raise RuntimeError("residents index: section headings moved")
    periods = []
    for era, text in (("card", card), ("reg", reg)):
        for lid, lab in re.findall(
                r'href="[^"]*lid=(\d{12})"[^>]*>(.*?)</a>', text, re.S):
            lab = norm(re.sub(r"<[^>]+>", "", lab))
            m = re.fullmatch(r"(\d{4})年(?:(\d{1,2})月末)?", lab)
            if not m:
                continue
            y = int(m.group(1))
            month = int(m.group(2) or 12)
            if month == 12 and Y0 <= y <= Y1:
                periods.append((era, y, lid))
    years = {e: sorted(y for ee, y, _ in periods if ee == e)
             for e in ("card", "reg")}
    print(f"  index: residence-card era {years['card'][0]}–"
          f"{years['card'][-1]}, registration era {years['reg'][0]}–"
          f"{years['reg'][-1]} (end-December editions)")
    if years["card"][0] != 2012 or years["reg"][-1] != 2011:
        raise SystemExit("  !! the July 2012 seam is not where it should be")

    out: dict[int, dict] = {}
    for era, y, lid in sorted(periods, key=lambda p: p[1]):
        ds = listing(lid)
        row = out.setdefault(y, {})
        if era == "reg":
            d = pick(ds, lid, lambda t: "在留資格" in t
                     and t.endswith("外国人登録者") and "都道府県" not in t
                     and "年齢" not in t)
            s = stock(workbook(d), card_era=False)
            row.update(registered_foreigners=s["total"],
                       registered_permanent_residents=s["permanent"],
                       registered_special_permanent_residents=
                       s["special_permanent"])
            continue
        d1 = pick(ds, lid, lambda t: t.startswith("国籍・地域別")
                  and "在留資格" in t and t.endswith("別在留外国人"))
        d2 = pick(ds, lid, lambda t: t.startswith("国籍・地域別")
                  and "在留資格" in t and t.endswith("総在留外国人"))
        s = stock(workbook(d1), card_era=True)
        s2 = stock(workbook(d2), card_era=False)
        row.update(foreign_residents=s["total"],
                   foreign_residents_all_statuses=s2["total"],
                   permanent_residents=s["permanent"],
                   special_permanent_residents=s["special_permanent"])
        for lab, col in NATIONALITIES.items():
            row[col] = s["nat"].get(lab)
        if s2["total"] <= s["total"]:
            raise SystemExit(f"  !! {y}: 総在留外国人 {s2['total']:,} not "
                             f"above 在留外国人 {s['total']:,}")
        print(f"    {y} {d1['num']}: {s['total']:,} "
              f"(all statuses {s2['total']:,})")

    for y, r in out.items():
        if r.get("foreign_residents") and r.get("registered_foreigners"):
            raise SystemExit(f"  !! {y} carries both regimes — the seam "
                             f"would be joined")
    check("在留外国人 end-2025", out[2025]["foreign_residents"], 4_125_395)
    check("総在留外国人 end-2025",
          out[2025]["foreign_residents_all_statuses"], 5_134_267)
    check("外国人登録者 end-2006", out[2006]["registered_foreigners"],
          2_084_919)
    check("外国人登録者 end-2011", out[2011]["registered_foreigners"],
          2_078_508)
    ratio = out[2025]["foreign_residents"] / CENSUS_2025_FOREIGN
    if not 1.0 < ratio < 1.15:
        raise SystemExit(f"  !! ISA/Census 2025 = {ratio:.3f}, outside "
                         f"1.00–1.15 — one of the stocks is wrong")
    print(f"  ok ISA end-2025 / Census 1 Oct 2025 foreign nationals = "
          f"{ratio:.3f} (ISA counts more: different date and scope)")

    header = (["year", "foreign_residents", "foreign_residents_all_statuses",
               "permanent_residents", "special_permanent_residents"]
              + list(NATIONALITIES.values())
              + ["registered_foreigners", "registered_permanent_residents",
                 "registered_special_permanent_residents"])
    return write("foreign_residents_from_isa.csv", header, out, """
Immigration Services Agency, 在留外国人統計 (table 1 / 1-2 of each
end-December edition) and, before the July 2012 break, 登録外国人統計
(table 1). PERSONS, stock at 31 December of `year`.
foreign_residents = 在留外国人: mid/long-term residents (residence-card
holders) + special permanent residents. Excludes short-term visitors,
diplomats and the undocumented. foreign_residents_all_statuses =
総在留外国人, every foreign national with a status (incl. short stay).
residents_* = 在留外国人 by NATIONALITY (citizenship, not birth); Japan
publishes no country-of-birth cut. residents_korea_incl_north (韓国・朝鮮)
and residents_korea_south (韓国) are different scopes from different
editions; never join them. China excludes Taiwan in this era.
registered_* = 外国人登録者, 2006-2011: the ABOLISHED alien-registration
regime, a different definition. HARD BREAK July 2012: the two regimes
never share a row and must never be drawn as one line.
""")


# -------------------------------------------------------------- entrants

def entrants_table(rows: list[list]) -> dict[int, tuple[int, int | None]]:
    """{year: (total, short_stay)} from the year rows of one edition."""
    i = next(k for k, r in enumerate(rows) if wareki(row_label(r)))
    cols = header_map(rows, i)
    # 短期滞在 is one column, or (older editions) 計 / 15日 / 90日以内.
    ss = [k for k in ("短期滞在", "短期滞在計") if k in cols]
    if "総数" not in cols or len(ss) != 1:
        raise RuntimeError(f"columns 総数/短期滞在 not found: {list(cols)}")
    cols["短期滞在"] = cols[ss[0]]
    out = {}
    for r in rows[i:]:
        lab = row_label(r)
        y = wareki(lab)
        if y is None:
            if lab and not any(isinstance(v, (int, float)) for v in r[1:4]):
                continue
            if lab:
                break  # the first nationality row ends the year block
            continue
        out[y] = (number(r[cols["総数"]]), number(r[cols["短期滞在"]]))
    return out


def entrants() -> int:
    print("ISA — 出入国管理統計 年報 (entrants, calendar year)")
    text = section(ENTRANTS_INDEX, 'id="a02"', 'id="a03"')
    editions = {}
    for lid, lab in re.findall(r'href="[^"]*lid=(\d{12})"[^>]*>(.*?)</a>',
                               text, re.S):
        m = re.fullmatch(r"(\d{4})年", norm(re.sub(r"<[^>]+>", "", lab)))
        if m and Y0 <= int(m.group(1)) <= Y1:
            editions[int(m.group(1))] = lid
    print(f"  index: {len(editions)} annual editions "
          f"{min(editions)}–{max(editions)}")
    if sorted(editions) != list(range(Y0, Y1 + 1)):
        raise SystemExit(f"  !! missing annual editions: "
                         f"{sorted(set(range(Y0, Y1 + 1)) - set(editions))}")

    new_by_ed: dict[int, dict] = {}
    all_by_ed: dict[int, dict] = {}
    for ed, lid in sorted(editions.items()):
        ds = listing(lid)
        dn = pick(ds, lid, lambda t: "新規入国外国人" in t and "在留資格" in t
                  and "入国目的" not in t)
        da = pick(ds, lid, lambda t: re.search(r"(?<!新規)(?<!出)入国外国人", t)
                  and "在留資格" in t and "再入国" not in t
                  and "新規" not in t)
        new_by_ed[ed] = entrants_table(workbook(dn))
        all_by_ed[ed] = entrants_table(workbook(da))
        if ed not in new_by_ed[ed] or ed not in all_by_ed[ed]:
            raise SystemExit(f"  !! edition {ed} has no row for its own year")
        print(f"    {ed} {dn['num']}/{da['num']}: new {new_by_ed[ed][ed][0]:,}"
              f", all {all_by_ed[ed][ed][0]:,}")

    def latest(by_ed: dict, label: str) -> dict[int, tuple]:
        """Each year from the newest edition that carries it; revisions
        between editions are printed, not hidden."""
        out = {}
        for ed in sorted(by_ed):
            for y, v in by_ed[ed].items():
                if Y0 <= y <= Y1:
                    if y in out and out[y] != v:
                        print(f"    revision {label} {y}: {out[y]} → {v} "
                              f"(edition {ed})")
                    out[y] = v
        return out

    new = latest(new_by_ed, "new entrants")
    allin = latest(all_by_ed, "all entrants")
    rows = {}
    for y in range(Y0, Y1 + 1):
        (nt, ns), (at, _) = new[y], allin[y]
        if at < nt:
            raise SystemExit(f"  !! {y}: all entrants {at:,} below new "
                             f"entrants {nt:,}")
        rows[y] = {"entrants_all": at, "new_entrants": nt,
                   "new_entrants_short_stay": ns,
                   "new_entrants_non_short_stay":
                       None if ns is None else nt - ns}
    check("new entrants 2025", rows[2025]["new_entrants"], 39_184_525)
    check("new entrants short stay 2025",
          rows[2025]["new_entrants_short_stay"], 38_458_105)
    check("new entrants NON-short-stay 2025",
          rows[2025]["new_entrants_non_short_stay"], 726_420)
    check("new entrants 2021 (border closure)", rows[2021]["new_entrants"],
          151_726)

    return write("entrants_from_isa.csv",
                 ["year", "entrants_all", "new_entrants",
                  "new_entrants_short_stay", "new_entrants_non_short_stay"],
                 rows, """
Immigration Services Agency, 出入国管理統計 年報 (annual): tables
国籍・地域別 在留資格別 入国外国人 (all entrants) and 新規入国外国人 (new
entrants), 総数 and 短期滞在 columns. ENTRIES (events, not persons),
calendar year. Each year is read from the newest edition carrying it.
entrants_all includes foreign residents re-entering on re-entry permits.
new_entrants = first entries; new_entrants_short_stay = 短期滞在
(tourists, business visitors); new_entrants_non_short_stay = new_entrants
- new_entrants_short_stay, computed here: the only one of these that is
migration. A new entrant is not an immigrant, and departures are not
emigrants. 2020-2022 are the border closures.
""")


# -------------------------------------------------------- naturalisation

def naturalisation() -> int:
    print("MOJ Civil Affairs Bureau — 帰化許可申請者数等の推移 (PDF)")
    links = page_links(NATURAL_PAGE)
    hrefs = {lab: h for h, lab in links if h.endswith(".pdf")}
    series = next((h for lab, h in hrefs.items()
                   if lab.startswith("帰化許可申請者数")), None)
    by_nat = next((h for lab, h in hrefs.items()
                   if lab.startswith("国籍別帰化許可者数")), None)
    if not series or not by_nat:
        raise RuntimeError(f"{NATURAL_PAGE}: PDF links not found {hrefs}")
    url = urllib.request.urljoin(NATURAL_PAGE, series)
    blob = get(url, is_pdf, CACHE / f"moj_{Path(series).name}")
    rows = {}
    with pdfplumber.open(io.BytesIO(blob)) as pdf:
        tables = [t for p in pdf.pages for t in p.extract_tables()]
        head = norm(pdf.pages[0].extract_text() or "")
    if "帰化許可申請者数" not in head or "不許可者数" not in head:
        raise RuntimeError("naturalisation PDF: unexpected title/headers")
    for t in tables:
        for r in t:
            y = wareki(r[0] or "")
            if y is None or not Y0 <= y <= Y1:
                continue
            if len(r) != 7:
                raise RuntimeError(f"naturalisation row {r}: 7 cells "
                                   f"expected")
            app, tot, kor, chn, oth, ref = (number(v) for v in r[1:])
            if tot != (kor or 0) + (chn or 0) + (oth or 0):
                raise SystemExit(f"  !! {y}: granted {tot} ≠ sum of "
                                 f"nationalities")
            rows[y] = {"applications": app, "granted": tot,
                       "granted_korea_incl_north": kor,
                       "granted_china": chn, "granted_other": oth,
                       "refused": ref}
    if sorted(rows) != list(range(Y0, Y1 + 1)):
        raise SystemExit(f"  !! naturalisation years {sorted(rows)}")
    check("帰化許可者数 2025", rows[2025]["granted"], 9_258)
    check("帰化許可申請者数 2025", rows[2025]["applications"], 14_103)
    check("帰化不許可者数 2025", rows[2025]["refused"], 666)
    check("帰化許可者数 2006", rows[2006]["granted"], 14_108)

    # Cross-check against the by-nationality PDF's 総数 row (same bureau,
    # separate table): the last three years must agree exactly.
    blob2 = get(urllib.request.urljoin(NATURAL_PAGE, by_nat), is_pdf,
                CACHE / f"moj_{Path(by_nat).name}")
    with pdfplumber.open(io.BytesIO(blob2)) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    yrs = [int(y) for y in re.findall(r"\((\d{4})\)", text)]
    tot_line = next(l for l in text.splitlines() if norm(l).startswith("総数"))
    tots = [int(x.replace(",", "")) for x in re.findall(r"[\d,]{3,}",
                                                         tot_line)]
    if len(yrs) != len(tots) or not yrs:
        raise RuntimeError(f"by-nationality PDF: years {yrs} totals {tots}")
    for y, v in zip(yrs, tots):
        check(f"granted {y} vs 国籍別帰化許可者数 総数", rows[y]["granted"], v)

    return write("naturalisation_from_moj.csv",
                 ["year", "applications", "granted",
                  "granted_korea_incl_north", "granted_china",
                  "granted_other", "refused"], rows, """
MOJ Civil Affairs Bureau, 帰化許可申請者数、帰化許可者数及び帰化不許可者数の
推移 (PDF). PERSONS, calendar year. applications, grants and refusals are
decisions in the year on DIFFERENT cohorts, not one cohort's outcome.
granted_* = former nationality of those granted (韓国・朝鮮 is one
category here). A grant moves a person out of the foreign-resident stock
without anybody moving.
""")


# ------------------------------------------- minimal BIFF8 (.xls) reader
#
# The pre-2016 ISA editions are Excel 97 .xls. xlrd is not importable
# under `python3 -I`, so this reads the cells a statistical table holds
# (shared strings, NUMBER/RK/MULRK, cached formula numbers) straight from
# the OLE compound file. Verified cell-for-cell against xlrd 2.0.2 on the
# 2006/2010/2011/2012 editions.

def _cfb_stream(blob: bytes, want: str) -> bytes:
    if blob[:8] != b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        raise ValueError("not an OLE compound file")
    ssz = 1 << struct.unpack_from("<H", blob, 30)[0]
    mssz = 1 << struct.unpack_from("<H", blob, 32)[0]
    dir_start, = struct.unpack_from("<I", blob, 48)
    cutoff, = struct.unpack_from("<I", blob, 56)
    minifat_start, = struct.unpack_from("<I", blob, 60)
    difat_start, difat_n = struct.unpack_from("<II", blob, 68)

    def sector(i):
        return blob[(i + 1) * ssz:(i + 2) * ssz]

    difat = list(struct.unpack_from("<109I", blob, 76))
    s = difat_start
    for _ in range(difat_n):
        if s >= 0xFFFFFFFA:
            break
        vals = struct.unpack(f"<{ssz // 4}I", sector(s))
        difat += vals[:-1]
        s = vals[-1]
    fat = []
    for f in difat:
        if f < 0xFFFFFFFA:
            fat += struct.unpack(f"<{ssz // 4}I", sector(f))

    def chain(start):
        out, s, seen = [], start, set()
        while s < 0xFFFFFFFA:
            if s in seen:
                raise ValueError("FAT loop")
            seen.add(s)
            out.append(sector(s))
            s = fat[s]
        return b"".join(out)

    d = chain(dir_start)
    entries = []
    for off in range(0, len(d), 128):
        e = d[off:off + 128]
        nlen, = struct.unpack_from("<H", e, 64)
        name = e[:max(nlen - 2, 0)].decode("utf-16-le", "replace")
        start, size = struct.unpack_from("<IQ", e, 116)
        entries.append((name, e[66], start, size & 0xFFFFFFFF))
    for name, typ, start, size in entries:
        if name == want and typ == 2:
            if size >= cutoff:
                return chain(start)[:size]
            ministream = chain(entries[0][2])
            mf = chain(minifat_start) if minifat_start < 0xFFFFFFFA else b""
            minifat = struct.unpack(f"<{len(mf) // 4}I", mf)
            out, s = [], start
            while s < 0xFFFFFFFA:
                out.append(ministream[s * mssz:(s + 1) * mssz])
                s = minifat[s]
            return b"".join(out)[:size]
    raise ValueError(f"no {want} stream")


def _rk(v: int) -> float:
    if v & 2:
        x = float(v >> 2 if v < 0x80000000 else (v >> 2) - (1 << 30))
    else:
        x = struct.unpack("<d", struct.pack("<Q", (v & 0xFFFFFFFC) << 32))[0]
    return x / 100 if v & 1 else x


def _parse_sst(chunks: list[bytes]) -> list[str]:
    ci, pos, data = 0, 8, chunks[0]
    _, n = struct.unpack_from("<II", data, 0)
    out = []
    for _ in range(n):
        if pos >= len(data):
            ci, pos = ci + 1, 0
            data = chunks[ci]
        cch, = struct.unpack_from("<H", data, pos)
        flags = data[pos + 2]
        pos += 3
        rich = ext = 0
        if flags & 0x08:
            rich, = struct.unpack_from("<H", data, pos)
            pos += 2
        if flags & 0x04:
            ext, = struct.unpack_from("<I", data, pos)
            pos += 4
        wide, parts, left = flags & 1, [], cch
        while left:
            if pos >= len(data):
                ci += 1
                data = chunks[ci]
                wide, pos = data[0] & 1, 1
            take = min(left, (len(data) - pos) // (2 if wide else 1))
            nb = take * (2 if wide else 1)
            seg = data[pos:pos + nb]
            parts.append(seg.decode("utf-16-le") if wide
                         else seg.decode("latin-1"))
            pos += nb
            left -= take
        skip = 4 * rich + ext
        while skip:
            if pos >= len(data):
                ci, pos = ci + 1, 0
                data = chunks[ci]
            t = min(skip, len(data) - pos)
            pos += t
            skip -= t
        out.append("".join(parts))
    return out


def xls_rows(blob: bytes, sheet: int = 0) -> list[list]:
    wb = None
    for name in ("Workbook", "Book"):
        try:
            wb = _cfb_stream(blob, name)
            break
        except ValueError:
            continue
    if wb is None:
        raise ValueError("no Workbook stream")
    recs, pos = [], 0
    while pos + 4 <= len(wb):
        rid, ln = struct.unpack_from("<HH", wb, pos)
        recs.append((rid, pos, wb[pos + 4:pos + 4 + ln]))
        pos += 4 + ln
    sst, sheets = [], []
    for k, (rid, pos, data) in enumerate(recs):
        if rid == 0x0085:
            sheets.append(struct.unpack_from("<I", data, 0)[0])
        elif rid == 0x00FC:
            chunks, j = [data], k + 1
            while j < len(recs) and recs[j][0] == 0x003C:
                chunks.append(recs[j][2])
                j += 1
            sst = _parse_sst(chunks)
        elif rid == 0x000A:
            break
    start, cells, on = sheets[sheet], {}, False
    for rid, pos, data in recs:
        if pos == start:
            on = True
            continue
        if not on:
            continue
        if rid == 0x000A:
            break
        if rid == 0x00FD:
            r, c, _, i = struct.unpack_from("<HHHI", data, 0)
            cells[(r, c)] = sst[i]
        elif rid == 0x0203:
            r, c, _, v = struct.unpack_from("<HHHd", data, 0)
            cells[(r, c)] = v
        elif rid == 0x027E:
            r, c, _, v = struct.unpack_from("<HHHI", data, 0)
            cells[(r, c)] = _rk(v)
        elif rid == 0x00BD:
            r, c0 = struct.unpack_from("<HH", data, 0)
            for i in range((len(data) - 6) // 6):
                _, v = struct.unpack_from("<HI", data, 4 + 6 * i)
                cells[(r, c0 + i)] = _rk(v)
        elif rid == 0x0006:
            r, c = struct.unpack_from("<HH", data, 0)
            if data[12:14] != b"\xff\xff":
                cells[(r, c)] = struct.unpack_from("<d", data, 6)[0]
        elif rid == 0x0204:
            r, c, _, n = struct.unpack_from("<HHHH", data, 0)
            raw = data[9:]
            cells[(r, c)] = (raw[:2 * n].decode("utf-16-le") if data[8] & 1
                             else raw[:n].decode("latin-1"))
    if not cells:
        return []
    rows = [[None] * (max(c for _, c in cells) + 1)
            for _ in range(max(r for r, _ in cells) + 1)]
    for (r, c), v in cells.items():
        rows[r][c] = v
    return rows


def main() -> None:
    residents()
    entrants()
    naturalisation()
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
