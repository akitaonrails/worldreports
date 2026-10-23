#!/usr/bin/env python3
"""Refresh the Statistics Bureau of Japan (MIC) series.

Usage:  python3 -I countries/japan/fetch/fetch_stat.py

Four products, all through file layers (no API key exists here):

  CPI         consumer price index, national and Tokyo ku-area
  LFS         labour force survey, annual averages (長期時系列表2)
  population  population estimates on 1 October (人口推計)
  census      2020 and 2025 population censuses (国勢調査)

**e-Stat, the anonymous file layer.** The e-Stat API needs an appId
(without one it answers HTTP 200 with RESULT.STATUS 100). The listing
pages `www.e-stat.go.jp/stat-search/files?…&layout=datalist&cycle=0`
are plain HTML, one `<article>` per file with its table number, title,
survey period and a `file-download?statInfId=…&fileKind=…` link. The
listing addresses (statistic, collection and class ids) are fixed here;
the statInfIds are read off the listing on every run and the file is
accepted only if its table number, title and download filename are the
expected ones. `cycle=0` is required, or the listing shows a tree
instead of the files.

**The CPI was rebased to 2025 in 2026, and both bases are published in
parallel.** e-Stat carries a long monthly series on each base (2020=100
and 2025=100, both from 1970) with its own published 12-month rates.
They are kept as separate columns and never joined: a rate is always
the publisher's rate within one base. The 2025-base file's rates for
months before 2026 repeat what was published on the 2020 base (the
fetcher counts how many months the two bases disagree and says so).
stat.go.jp's three-decimal files (zmi2020aa, zmi2025aa, tmi2025aa,
linked from /data/cpi/1.html) are used to check the long series
month by month.

**The LFS is in units of 10,000 persons (万人).** Every count is
multiplied by ten here and written in thousands; rates are untouched.
The long table is a publisher-spliced series: 2005–09 rest on the
2010-census benchmark, 2010–14 on 2015, 2015 onward on 2020 (asserted
from the workbook's own note and written as a column). The 2011 annual
figures are supplementary estimates: Iwate, Miyagi and Fukushima were
not surveyed March–August 2011.

**Population: estimates and census are two series.** The estimates for
2000–2020 are intercensally adjusted onto the censuses (e-Stat long
table); 2021–2024 come from each year's annual release
(stat.go.jp/data/jinsui/<Y>np/), still on the 2020-census base. There
is no 2025 annual release: census years are replaced by the census,
and the 2021–2025 estimates have not yet been re-based onto the 2025
census. Until they are, growth across 2024→2025 between the two files
is a change of base, not growth; the census is written to its own file.

**The census figures are the imputed reference tables (不詳補完値).**
The raw tables leave nationality "unknown" unassigned (raw 2025
Japanese = 117.4mn); the published summary (122,973k total, 119,132k
Japanese, 3,840k foreign) is the imputed table, so that is the one
taken. Foreign = total − Japanese, computed and labelled.

Spot values asserted (DISCOVERY.md / SOURCES.yaml): CPI annual-average
rates 2022 +2.5, 2023 +3.3, 2024 +2.7, 2025 +3.2 (2020 base, from the
index); unemployment 2006 4.1, 2009 5.1, 2011 4.6, 2024 2.5, 2025 2.5,
labour force 2025 = 7,004万; population 2006 127,901k, 2010 128,057k,
2015 127,095k, 2020 126,146k, 2024 123,802k; census 2025 122,973k /
119,132k / 3,840k, foreign +39.8% on 2020. Second sources: World Bank
mid-2024 population 123.98mn against the 1 October 2024 estimate; the
2025 census population aged 15+ against the LFS 2025 15+ population;
the 2020 census against the estimates' 2020 row.

Outputs are `_from_stat` sidecars under data/. Nothing here overwrites
a curated file.
"""
from __future__ import annotations

import csv
import html
import io
import re
import sys
import textwrap
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import warnings
import zipfile
from pathlib import Path

try:
    import openpyxl
except ImportError:
    sys.exit("openpyxl is required: pip install -r requirements-fetch.txt")

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache"

ESTAT = "https://www.e-stat.go.jp"
STAT = "https://www.stat.go.jp"
UA = {"User-Agent": "worldreports-fetch"}
GAP = 2.0                 # seconds between requests
Y0 = 2006                 # the atlas window opens here
LAST_FULL = 2025          # country.yaml last_full_year

WB_POP_2024 = 123.98e6    # World Bank SP.POP.TOTL, JPN, 2024 (mid-year)

# e-Stat listing addresses: statistic / collection / class ids. These
# are the stable part; the files under them are resolved per run.
L_CPI2020_M = dict(toukei="00200573", tstat="000001150147",
                   tclass1="000001150151", tclass2="000001150152",
                   tclass3="000001150153", tclass4="000001150156")
L_CPI2025_M = dict(toukei="00200573", tstat="000001243876",
                   tclass1="000001243880", tclass2="000001243881",
                   tclass3="000001243883", tclass4="000001243886")
L_CPI2025_TOKYO_M = dict(toukei="00200573", tstat="000001243876",
                         tclass1="000001243880", tclass2="000001243881",
                         tclass3="000001243884", tclass4="000001243888")
L_LFS = dict(tclass="000001226526")
L_POP_LONG = dict(toukei="00200524", tstat="000000090001",
                  tclass1="000000090004", tclass2="000001051180")
# 2025 census, 参考表：不詳補完値 (imputed), basic tabulation: the 2025
# results and the 2020 results re-tabulated with the same imputation.
L_CENSUS_IMPUTED = {
    2025: dict(toukei="00200521", tstat="000001230925",
               tclass1="000001230928", tclass2="000001244578",
               tclass3="000001244579"),
    2020: dict(toukei="00200521", tstat="000001230925",
               tclass1="000001230928", tclass2="000001230929",
               tclass3="000001230930"),
}


# ---------------------------------------------------------------- transport

_last = [0.0]


def _get(url: str) -> tuple[bytes, dict]:
    """One request, spaced, retried, backing off on 429/403."""
    last = None
    for attempt in range(4):
        wait = _last[0] + GAP - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=300) as r:
                blob, head = r.read(), dict(r.headers)
            _last[0] = time.monotonic()
            return blob, head
        except urllib.error.HTTPError as e:
            _last[0] = time.monotonic()
            last = e
            if e.code == 404:
                break
            time.sleep(30 * (attempt + 1) if e.code in (429, 403) else 3)
        except OSError as e:
            _last[0] = time.monotonic()
            last = e
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"{url}: {last}")


def fetch(url: str, name: str, check, fresh: bool = False) -> bytes:
    """Cached download; `check(blob, headers)` raises before caching.
    Listing and index pages are fetched `fresh` every run."""
    CACHE.mkdir(exist_ok=True)
    local = CACHE / name
    if local.exists() and not fresh:
        return local.read_bytes()
    print(f"  downloading {url}")
    blob, head = _get(url)
    check(blob, head)
    local.write_bytes(blob)
    return blob


def filename(head: dict) -> str:
    cd = head.get("Content-Disposition") or head.get("content-disposition") or ""
    m = re.search(r"filename\*=UTF-8''([^;]+)", cd) or \
        re.search(r'filename="?([^";]+)', cd)
    return urllib.parse.unquote(m[1]) if m else ""


def is_xlsx(blob: bytes) -> None:
    if blob[:2] != b"PK":
        raise RuntimeError("payload is not an xlsx (error page?)")
    bad = zipfile.ZipFile(io.BytesIO(blob)).testzip()
    if bad:
        raise RuntimeError(f"xlsx member {bad} is corrupt")


def is_cp932_csv(min_rows: int):
    def check(blob: bytes, head: dict = None) -> None:
        if blob[:200].lower().lstrip().startswith(b"<"):
            raise RuntimeError("CSV payload is HTML (error page?)")
        text = blob.decode("cp932")
        if len(re.findall(r"^\d{6},", text, re.M)) < min_rows:
            raise RuntimeError(f"fewer than {min_rows} monthly rows")
    return check


def page_check(marker: bytes):
    def check(blob: bytes, head: dict) -> None:
        if marker not in blob:
            raise RuntimeError(f"page lacks {marker!r} (moved or walled?)")
    return check


def label(v) -> str:
    return unicodedata.normalize("NFKC", str(v if v is not None else "")).strip()


def num(v) -> float | None:
    if isinstance(v, (int, float)):
        return float(v)
    t = label(v).replace(",", "")
    return float(t) if re.fullmatch(r"-?\d+(\.\d+)?", t) else None


# ---------------------------------------------------------------- e-Stat

def estat_listing(params: dict, tag: str) -> list[dict]:
    """The files of one e-Stat listing, as dicts with group, table, id,
    title, period and the fileKinds offered."""
    q = dict(page="1", layout="datalist", cycle="0", **params)
    url = f"{ESTAT}/stat-search/files?" + urllib.parse.urlencode(q)
    t = fetch(url, f"stat_listing_{tag}.html",
              page_check(b"stat-dataset_list-item"),
              fresh=True).decode("utf-8", "replace")
    out, group = [], ""
    for art in t.split('<article class="stat-dataset_list-item">')[1:]:
        if "stat-dataset_list-detail" not in art:
            g = re.search(r'stat-dataset_list-group-item">\s*([^<]+)', art)
            group = label(html.unescape(g[1])) if g else group
            continue
        tab = re.search(r"表番号&nbsp;</span><span>([^<]*)</span>", art)
        tit = re.search(r'data-value="(\d{12})"[^>]*>\s*([^<]+?)\s*</a>',
                        art, re.S)
        per = re.search(r"調査年月&nbsp;&nbsp;</span>\s*([^<]+)", art)
        if not tit:
            continue
        out.append({"group": group, "table": label(tab[1]) if tab else "",
                    "id": tit[1], "title": label(html.unescape(tit[2])),
                    "period": label(per[1]) if per else "",
                    "kinds": set(re.findall(
                        rf"statInfId={tit[1]}&fileKind=(\d)", art))})
    if not out:
        raise RuntimeError(f"{tag}: e-Stat listing lists no files")
    return out


def pick(files: list[dict], tag: str, *, title: str, table: str = None,
         group: str = None, period: str = None) -> dict:
    hits = [f for f in files if re.search(title, f["title"])
            and (table is None or f["table"] == table)
            and (group is None or group in f["group"])
            and (period is None or f["period"] == period)]
    if len(hits) != 1:
        raise RuntimeError(f"{tag}: {len(hits)} files match title "
                           f"{title!r} table {table!r} period {period!r}")
    return hits[0]


def estat_file(f: dict, kind: str, expect: str, check, tag: str) -> bytes:
    """Download one listed file; the content-disposition filename must
    match `expect`. Cached per statInfId and survey period, so a monthly
    update of a long series (same id) is a new cache entry."""
    if kind not in f["kinds"]:
        raise RuntimeError(f"{tag}: fileKind {kind} not offered "
                           f"({sorted(f['kinds'])})")
    url = (f"{ESTAT}/stat-search/file-download?statInfId={f['id']}"
           f"&fileKind={kind}")
    per = re.sub(r"\D", "", f["period"])

    def full(blob, head):
        got = filename(head)
        if not re.fullmatch(expect, got):
            raise RuntimeError(f"{tag}: e-Stat served {got!r}, "
                               f"expected {expect!r}")
        check(blob, head)

    ext = ".csv" if kind == "1" else ".xlsx"
    return fetch(url, f"stat_{tag}_{f['id']}_{per}{ext}", full)


def xlsx_check(blob, head=None):
    is_xlsx(blob)


def workbook(blob: bytes):
    return openpyxl.load_workbook(io.BytesIO(blob), read_only=True,
                                  data_only=True)


# ---------------------------------------------------------------- writers

def write(rel: str, comment: str, header: list[str], rows: list[list]) -> None:
    path = DATA / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        for line in comment.strip().splitlines():
            # Interpolated lists can run long; fold them, keep the rest.
            for part in textwrap.wrap(line, 76) or [""]:
                fh.write(f"# {part}".rstrip() + "\n")
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    span = f"{rows[0][0]}–{rows[-1][0]}" if rows else "EMPTY"
    print(f"  data/{rel}  {len(rows)} rows ({span})")


def fmt(v, nd: int = 1):
    if v is None:
        return ""
    return int(round(v)) if nd == 0 else round(v, nd)


def near(a, b, tol, what):
    if a is None or b is None or abs(a - b) > tol:
        raise RuntimeError(f"{what}: {a} vs {b} (tolerance {tol})")


# ---------------------------------------------------------------- CPI

CODES = {"0001": "all", "0161": "core", "0178": "corecore"}


def cpi_csv(blob: bytes, what: str) -> dict[str, dict[str, float | None]]:
    """{'all'|'core'|'corecore': {'YYYY-MM': value}} from a CPI CSV
    (one column per item; row 3 holds the item codes)."""
    rows = list(csv.reader(io.StringIO(blob.decode("cp932"))))
    code_row = next(r for r in rows[:6] if r and "符号" in r[0])
    idx = {}
    for code, name in CODES.items():
        hits = [i for i, c in enumerate(code_row) if c.strip() == code]
        if len(hits) != 1:
            raise RuntimeError(f"{what}: item code {code} found {len(hits)}×")
        idx[name] = hits[0]
    out = {n: {} for n in CODES.values()}
    for r in rows:
        if r and re.fullmatch(r"\d{6}", r[0]):
            m = f"{r[0][:4]}-{r[0][4:]}"
            for n, i in idx.items():
                out[n][m] = num(r[i]) if i < len(r) else None
    return out


def cpi_long(listing: dict, tag: str, base: str, region: str) -> tuple:
    files = estat_listing(listing, tag)
    lev = pick(files, tag, title=r"^中分類指数\(1970年1月", group=region)
    yoy = pick(files, tag, title=r"^中分類指数\s*前年同月比", group=region)
    if lev["period"] != yoy["period"]:
        raise RuntimeError(f"{tag}: index {lev['period']} vs rates "
                           f"{yoy['period']}")
    p = "z" if region == "全国" else "[tk]"
    a = cpi_csv(estat_file(lev, "1", rf"{p}mi{base}s\.csv",
                           is_cp932_csv(500), f"{tag}_index"), tag)
    b = cpi_csv(estat_file(yoy, "1", rf"{p}my{base}s\.csv",
                           is_cp932_csv(500), f"{tag}_yoy"), tag)
    return a, b, lev["period"]


def cpi_aa(base: str, prefix: str) -> dict:
    """The three-decimal current-base file linked from /data/cpi/1.html."""
    page = fetch(f"{STAT}/data/cpi/1.html", "stat_cpi_1.html",
                 page_check(b"csv"), fresh=True).decode("cp932", "replace")
    rel = f"/data/cpi/{base}/csv/{prefix}mi{base}aa.csv"
    if f'href="{rel}"' not in page:
        raise RuntimeError(f"/data/cpi/1.html no longer links {rel}")
    blob = fetch(STAT + rel, f"stat_{prefix}mi{base}aa.csv",
                 is_cp932_csv(12), fresh=True)
    return cpi_csv(blob, rel)


def check_against_aa(long: dict, aa: dict, what: str) -> None:
    n = 0
    for k, s in aa.items():
        for m, v in s.items():
            if v is None or long[k].get(m) is None:
                continue
            # The long series is the three-decimal index rounded to one.
            near(long[k][m], v, 0.051, f"{what} {k} {m}: long vs aa file")
            n += 1
    if n < 30:
        raise RuntimeError(f"{what}: only {n} months overlap the aa file")


def check_rates(level: dict, rate: dict, what: str) -> list[str]:
    """Published 12-month rates against the one-decimal index.

    The publisher keeps each month's rate as first published, on the
    base then in force, while the index is relinked to the current
    base. The two can therefore disagree only in base years (2010,
    2015, 2020, 2025: the year a new base takes effect for the index
    but rates were still published on the old one). A disagreement in
    any other year raises; base-year ones are returned for the comment.
    """
    odd = []
    for m, v in rate.items():
        y, mo = m.split("-")
        prev = f"{int(y) - 1}-{mo}"
        if v is None or int(y) < Y0 or level.get(prev) is None:
            continue
        calc = (level[m] / level[prev] - 1) * 100
        if abs(v - calc) > 0.2:
            if int(y) % 5:
                raise RuntimeError(f"{what} {m}: published rate {v} vs "
                                   f"{calc:.2f} from the index")
            odd.append(m)
    return odd


def annual_rate(s: dict, y: int) -> float:
    cur = [s[f"{y}-{m:02d}"] for m in range(1, 13)]
    pre = [s[f"{y - 1}-{m:02d}"] for m in range(1, 13)]
    return (sum(cur) / sum(pre) - 1) * 100


def cpi() -> None:
    l20, r20, p20 = cpi_long(L_CPI2020_M, "cpi2020", "2020", "全国")
    l25, r25, p25 = cpi_long(L_CPI2025_M, "cpi2025", "2025", "全国")
    check_against_aa(l20, cpi_aa("2020", "z"), "CPI 2020 base")
    aa25 = cpi_aa("2025", "z")
    check_against_aa(l25, aa25, "CPI 2025 base")
    odd = sorted({m for k in CODES.values()
                  for m in check_rates(l20[k], r20[k], f"CPI 2020 {k}")
                  + check_rates(l25[k], r25[k], f"CPI 2025 {k}")})
    # 2025 = 100 on its own base: the mean of the 2025 months.
    mean25 = sum(aa25["all"][f"2025-{m:02d}"] for m in range(1, 13)) / 12
    near(mean25, 100.0, 0.01, "2025-base index, 2025 average")
    # Spot values (DISCOVERY.md), computed on the 2020 base from the
    # three-decimal file, one decimal.
    aa20 = cpi_aa("2020", "z")
    for y, want in ((2022, 2.5), (2023, 3.3), (2024, 2.7), (2025, 3.2)):
        # DISCOVERY rounded half-up (2023: 3.25 -> 3.3); compare unrounded.
        near(annual_rate(aa20["all"], y), want, 0.06,
             f"CPI 2020 base, {y} annual-average rate")
    # How far the 2025-base file's pre-2026 rates are the old base's.
    same = sum(1 for m, v in r25["all"].items()
               if m < "2026-01" and m >= f"{Y0}-01" and v is not None
               and v == r20["all"].get(m))
    total = sum(1 for m, v in r25["all"].items()
                if m < "2026-01" and m >= f"{Y0}-01" and v is not None)
    diff26 = [m for m, v in r25["all"].items() if m >= "2026-01"
              and v is not None and r20["all"].get(m) is not None
              and v != r20["all"][m]]
    print(f"  CPI: {same}/{total} pre-2026 monthly rates identical on both "
          f"bases; {len(diff26)} months of 2026 differ")
    months = sorted(m for m in set(l20["all"]) | set(l25["all"])
                    if m >= f"{Y0}-01")
    names = list(CODES.values())
    write("macro/cpi_from_stat.csv", f"""
Statistics Bureau of Japan (MIC), Consumer Price Index, NATIONAL,
monthly, via e-Stat long series (中分類指数 and 中分類指数 前年同月比),
latest month {p20} (2020 base) / {p25} (2025 base). TWO BASES, NEVER
JOINED: cpi2020_* is 2020=100 (the base in force until 2026), cpi2025_*
is 2025=100 (rebased in 2026, carried back to 1970 by the publisher).
all = 総合 (all items); core = 生鮮食品を除く総合 (less fresh food, the
BoJ's reference); corecore = 生鮮食品及びエネルギーを除く総合 (less fresh
food and energy). Index levels are the publisher's one-decimal long
series; *_yoy_pct are the PUBLISHED 12-month % changes of each base
(not computed). The 2025-base rates for months before 2026-01 repeat
the 2020-base published rates ({same} of {total} months identical);
from 2026-01 the bases give different rates ({len(diff26)} months
differ), so a rate line must stay on one base. Rates are kept as FIRST
PUBLISHED on the base then in force, while the index is relinked, so in
base-change years a rate need not match the index printed beside it
(months off by more than 0.2pt on this run: {', '.join(odd) or 'none'}).
Checked month by month against stat.go.jp's three-decimal files
zmi2020aa/zmi2025aa.
""", ["month"] + [f"cpi2020_{n}" for n in names]
          + [f"cpi2020_{n}_yoy_pct" for n in names]
          + [f"cpi2025_{n}" for n in names]
          + [f"cpi2025_{n}_yoy_pct" for n in names],
          [[m] + [fmt(l20[n].get(m)) for n in names]
           + [fmt(r20[n].get(m)) for n in names]
           + [fmt(l25[n].get(m)) for n in names]
           + [fmt(r25[n].get(m)) for n in names] for m in months])

    lt, rt, pt = cpi_long(L_CPI2025_TOKYO_M, "cpi2025tokyo", "2025",
                          "東京都区部")
    check_against_aa(lt, cpi_aa("2025", "t"), "Tokyo CPI 2025 base")
    odd_t = sorted({m for k in CODES.values()
                    for m in check_rates(lt[k], rt[k], f"Tokyo CPI {k}")})
    last_nat = max(m for m, v in l25["all"].items() if v is not None)
    last_tok = max(m for m, v in lt["all"].items() if v is not None)
    print(f"  CPI: national to {last_nat}, Tokyo to {last_tok}")
    if last_tok < last_nat:
        raise RuntimeError("Tokyo CPI is behind the national CPI")
    months = sorted(m for m in lt["all"] if m >= f"{Y0}-01")
    write("macro/cpi_tokyo_from_stat.csv", f"""
Statistics Bureau of Japan (MIC), Consumer Price Index, TOKYO KU-AREA
(東京都区部) only, 2025=100, monthly, via e-Stat long series, latest
month {pt}. Tokyo is published about a month ahead of the national CPI
(national to {last_nat}, Tokyo to {last_tok} on this run): a leading
indicator, never drawn as the national rate. Columns as in
cpi_from_stat.csv; *_yoy_pct are the published 12-month % changes on
the 2025 base (before 2026 they repeat the rates published on the 2020
base, as first published; base-year months off the index by more
than 0.2pt: {', '.join(odd_t) or 'none'}). Checked against stat.go.jp's
three-decimal file tmi2025aa.
""", ["month"] + [f"tokyo2025_{n}" for n in names]
          + [f"tokyo2025_{n}_yoy_pct" for n in names],
          [[m] + [fmt(lt[n].get(m)) for n in names]
           + [fmt(rt[n].get(m)) for n in names] for m in months])


# ---------------------------------------------------------------- LFS

def labour() -> dict:
    files = estat_listing(L_LFS, "lfs")
    f = pick(files, "lfs", title=r"^1953年", table="2-1", group="年平均")
    wb = workbook(estat_file(f, "0", r"lt02\.xlsx", xlsx_check, "lfs"))
    if "長期02" not in wb.sheetnames:
        raise RuntimeError(f"lt02.xlsx sheets {wb.sheetnames}")
    rows = list(wb["長期02"].iter_rows(values_only=True))
    notes = " ".join(label(c) for r in wb["※注_Notes"].iter_rows(values_only=True)
                     for c in r if c)
    # The header, by position, asserted.
    if label(rows[3][2]) != "(万人)":
        raise RuntimeError(f"LFS unit is {rows[3][2]!r}, not 万人")
    want = {2: "15歳以上人口", 3: "労働力人口", 6: "非労働力人口",
            10: "労働力人口", 11: "就業率", 12: "完全失業率",
            23: "完全失業率", 34: "完全失業率"}
    for i, w in want.items():
        if not label(rows[5][i]).startswith(w):
            raise RuntimeError(f"LFS column {i} is {rows[5][i]!r}")
    if label(rows[4][2]) != "男女計" or label(rows[4][13]) != "男" \
            or label(rows[4][24]) != "女":
        raise RuntimeError("LFS sex blocks moved")
    if label(rows[7][4]) != "就業者" or label(rows[7][5]) != "完全失業者":
        raise RuntimeError("LFS employed/unemployed columns moved")
    for frag in ("2005年から2009年までの数値については2010年国勢調査基準",
                 "2010年から2014年までの数値については2015年国勢調査基準",
                 "2020年国勢調査結果を基準とする推計人口(新基準)に切り替えた",
                 "2011年の< >内の数値は補完的に推計した値"):
        if frag not in notes:
            raise RuntimeError(f"LFS notes changed; lost {frag!r}")

    data = {}
    for r in rows[10:]:
        if isinstance(r[1], (int, float)) and 1950 < r[1] < 2100:
            data[int(r[1])] = r
    for y in range(Y0, LAST_FULL + 1):
        if y not in data:
            raise RuntimeError(f"LFS: year {y} missing")
    # Spot values.
    for y, want_u in ((2006, 4.1), (2009, 5.1), (2011, 4.6), (2024, 2.5),
                      (2025, 2.5)):
        near(num(data[y][12]), want_u, 0.001, f"LFS unemployment {y}")
    near(num(data[2025][3]), 7004, 0.001, "LFS labour force 2025 (万人)")
    for y in range(Y0, max(data) + 1):
        r = data[y]
        # The spliced comparable series is adjusted column by column, so
        # employed + unemployed may miss the labour force by a few 万人.
        near(num(r[4]) + num(r[5]), num(r[3]), 0.001 * num(r[3]),
             f"LFS {y} E+U vs LF")
        near(num(r[5]) / num(r[3]) * 100, num(r[12]), 0.1,
             f"LFS {y} unemployment rate vs counts")

    def bench(y):
        return 2010 if y <= 2009 else 2015 if y <= 2014 else 2020

    def k(v):  # 万人 → thousands
        x = num(v)
        return None if x is None else x * 10

    years = [y for y in sorted(data) if y >= Y0]
    write("social/labour_from_stat.csv", f"""
Statistics Bureau of Japan (MIC), Labour Force Survey, 長期時系列表2
(lt02.xlsx, e-Stat table 2-1, annual averages, whole Japan), sheet 長期02
(the current spliced series; the sheet 長期02 (既公表値) of previously
published values is NOT used). COUNTS ARE THOUSANDS OF PERSONS,
converted here from the published 万人 (10,000 persons) by x10; rates
are the published %, aged 15+. benchmark_census is the census whose
population estimates the year is benchmarked on, per the workbook's
note 3 (2005-09: 2010 census; 2010-14: 2015; 2015 on: 2020): each switch
is a level shift, not a change in the labour market. supplementary=1
marks 2011, a supplementary estimate (Iwate, Miyagi and Fukushima were
not surveyed Mar-Aug 2011 after the earthquake). Calendar years. The
fiscal-year twin (table 2-2) is not taken.
""", ["year", "pop_15plus_k", "labour_force_k", "employed_k",
      "unemployed_k", "not_in_labour_force_k", "participation_rate_pct",
      "employment_rate_pct", "unemployment_rate_pct",
      "unemployment_rate_male_pct", "unemployment_rate_female_pct",
      "benchmark_census", "supplementary"],
          [[y, fmt(k(data[y][2]), 0), fmt(k(data[y][3]), 0),
            fmt(k(data[y][4]), 0), fmt(k(data[y][5]), 0),
            fmt(k(data[y][6]), 0), fmt(num(data[y][10])),
            fmt(num(data[y][11])), fmt(num(data[y][12])),
            fmt(num(data[y][23])), fmt(num(data[y][34])), bench(y),
            1 if y == 2011 else ""] for y in years])
    return {"pop15_2025_k": k(data[2025][2])}


# ---------------------------------------------------------------- population

def pop_long() -> dict[int, dict]:
    files = estat_listing(L_POP_LONG, "poplong")
    f = pick(files, "poplong", title=r"総人口、日本人人口\(2000年~2020年\)",
             table="1")
    wb = workbook(estat_file(f, "4", r"05k\d+-1\.xlsx", xlsx_check, "poplong"))
    out = {}
    for sheet in wb.sheetnames:
        rows = list(wb[sheet].iter_rows(values_only=True))
        if not any("千人" in label(c) for r in rows[:6] for c in r):
            raise RuntimeError(f"pop long {sheet}: unit is not 千人")
        notes = {}
        for r in rows:
            m = re.match(r"注?\s*(\d)\)\s*(.+)", label(r[0]))
            if m:  # Japanese note first; the English twin must not win
                notes.setdefault(m[1], m[2])
        if "*" not in " ".join(label(r[0]) for r in rows) or \
                not any("補間補正" in label(r[0]) for r in rows):
            raise RuntimeError(f"pop long {sheet}: intercensal note gone")
        for r in rows:
            cells = list(r)
            yi = next((i for i, c in enumerate(cells[:3])
                       if isinstance(c, int) and 1990 < c < 2100), None)
            if yi is None:
                continue
            y = cells[yi]
            note = label(cells[yi + 1]).rstrip(")") if \
                isinstance(cells[yi + 1], str) else ""
            vals = [num(c) for c in cells[yi + 1:] if num(c) is not None][:6]
            if len(vals) != 6:
                raise RuntimeError(f"pop long {sheet} {y}: {vals}")
            census = bool(note) and "国勢調査" in notes.get(note, "")
            rec = dict(zip(("total", "male", "female", "japanese",
                            "japanese_male", "japanese_female"), vals),
                       basis="census" if census else "intercensal_adjusted")
            if y in out and out[y] != rec:
                raise RuntimeError(f"pop long: {y} differs between sheets")
            out[y] = rec
    return out


def pop_annual(after: int) -> dict[int, dict]:
    idx = fetch(f"{STAT}/data/jinsui/2.html", "stat_jinsui_2.html",
                page_check(b"np/index.html"),
                fresh=True).decode("cp932", "replace")
    years = sorted({int(y) for y in re.findall(
        r'href="/data/jinsui/(\d{4})np/index\.html"', idx) if int(y) > after})
    if not years:
        raise RuntimeError("no annual population release after the long table")
    out = {}
    for y in years:
        page = fetch(f"{STAT}/data/jinsui/{y}np/index.html",
                     f"stat_jinsui_{y}np.html", page_check(b"zuhyou"),
                     fresh=True)
        try:
            page = page.decode("utf-8")
        except UnicodeDecodeError:
            page = page.decode("cp932", "replace")
        rel = f"/data/jinsui/{y}np/zuhyou/05k{y}-1.xlsx"
        if f'href="{rel}"' not in page:
            raise RuntimeError(f"{y}np index does not link {rel}")
        wb = workbook(fetch(STAT + rel, f"stat_05k{y}-1.xlsx",
                            lambda b, h: is_xlsx(b)))
        rows = list(wb[wb.sheetnames[0]].iter_rows(values_only=True))
        title = " ".join(label(c) for r in rows[:2] for c in r if c)
        if f"{y}年10月1日現在" not in title or "日本人人口" not in title:
            raise RuntimeError(f"05k{y}-1: title {title!r}")
        head = [label(c) for c in rows[9][:8]]
        if head[1:4] != ["男 女 計", "男", "女"] or head[5] != "男 女 計":
            raise RuntimeError(f"05k{y}-1: header {head}")
        tot = next(r for r in rows if re.fullmatch(r"総\s*数", label(r[0])))
        out[y] = dict(total=num(tot[1]), male=num(tot[2]),
                      female=num(tot[3]), japanese=num(tot[5]),
                      japanese_male=num(tot[6]), japanese_female=num(tot[7]),
                      basis="estimate_2020_census_base")
    return out


def population() -> dict:
    data = pop_long()
    data.update(pop_annual(max(data)))
    for y, want in ((2006, 127_901), (2010, 128_057), (2015, 127_095),
                    (2020, 126_146), (2024, 123_802)):
        near(data[y]["total"], want, 0.001, f"population {y} (thousands)")
    for y in (2010, 2015, 2020):
        if data[y]["basis"] != "census":
            raise RuntimeError(f"population {y} is not flagged as census")
    for y, d in data.items():
        near(d["male"] + d["female"], d["total"], 1.01, f"population {y} M+F")
    if abs(data[2024]["total"] * 1000 / WB_POP_2024 - 1) > 0.005:
        raise RuntimeError(f"population 2024 {data[2024]['total']}k vs World "
                           f"Bank {WB_POP_2024 / 1e6:.2f}mn")
    years = sorted(y for y in data if y >= Y0)
    gap = [y for y in range(Y0, years[-1] + 1) if y not in data]
    write("demography/population_from_stat.csv", f"""
Statistics Bureau of Japan (MIC), Population Estimates (人口推計), total
and JAPANESE population on 1 OCTOBER, THOUSANDS of persons. 2000-2020
from the e-Stat long table (第1表, intercensally adjusted onto the
censuses); {min(y for y in data if data[y]['basis'] == 'estimate_2020_census_base')}
onward from each year's annual release (05k<Y>-1.xlsx). basis:
census = the census count itself; intercensal_adjusted = estimate
revised onto the following census; estimate_2020_census_base = not yet
revised. 2025 IS ABSENT ON PURPOSE: there is no 2025 annual estimate
(census years are replaced by the census, see census_from_stat.csv),
and the 2021-2024 rows will be re-based onto the 2025 census, which
counted fewer people than these estimates imply: growth from 2024 here
to 2025 there is a change of base, not growth. foreign = total -
japanese, COMPUTED here; Japanese includes a pro-rated share of persons
of unknown nationality (publisher's note). Missing years: {gap or 'none'}.
Cross-check: 2024 = {data[2024]['total']:,.0f}k vs World Bank mid-year
{WB_POP_2024 / 1e6:.2f}mn.
""", ["year", "population_k", "male_k", "female_k", "japanese_k",
      "foreign_k", "basis"],
          [[y, fmt(data[y]["total"], 0), fmt(data[y]["male"], 0),
            fmt(data[y]["female"], 0), fmt(data[y]["japanese"], 0),
            fmt(data[y]["total"] - data[y]["japanese"], 0), data[y]["basis"]]
           for y in years])
    return data


# ---------------------------------------------------------------- census

def census_year(year: int) -> dict:
    files = estat_listing(L_CENSUS_IMPUTED[year], f"census{year}")
    f = pick(files, f"census{year}", title=r"^男女[、,]\s*年齢\(5歳階級及び3区分\)",
             table="2-3", period=f"{year}年10月")
    wb = workbook(estat_file(f, "0", r"s?wb02_03\.xlsx", xlsx_check,
                             f"census{year}"))
    rows = list(wb[wb.sheetnames[0]].iter_rows(values_only=True))
    era = {2025: "令和7年", 2020: "令和2年"}[year]
    if not label(rows[0][0]).startswith("【不詳補完値】") or \
            era not in label(rows[0][0]):
        raise RuntimeError(f"census {year}: title {rows[0][0]!r} is not the "
                           f"imputed {era} table")
    block, names = rows[5], rows[7]
    want = {"total": "00_総数", "age_0_14": "R1_(再掲)15歳未満",
            "age_15_64": "R2_(再掲)15～64歳", "age_65plus": "R3_(再掲)65歳以上",
            "age_unknown": "24_年齢「不詳」"}
    ci = {}
    for k, n in want.items():
        hits = [i for i, c in enumerate(names)
                if label(c) == unicodedata.normalize("NFKC", n)
                and label(block[i]) == "人口"]
        if len(hits) != 1:
            raise RuntimeError(f"census {year}: column {n!r} found "
                               f"{len(hits)}× in the 人口 block")
        ci[k] = hits[0]
    if label(rows[9][ci["total"]]) != "人":
        raise RuntimeError(f"census {year}: unit is not persons")
    out = {}
    for r in rows:
        if label(r[3]) == "00000_全国" and label(r[1]) == "0_総数":
            key = {"0_国籍総数": "all", "1_うち日本人": "japanese"}.get(label(r[0]))
            if key:
                out[key] = {k: num(r[i]) for k, i in ci.items()}
    if set(out) != {"all", "japanese"}:
        raise RuntimeError(f"census {year}: national rows {sorted(out)}")
    for k in ("all", "japanese"):
        parts = sum(out[k][a] or 0 for a in
                    ("age_0_14", "age_15_64", "age_65plus", "age_unknown"))
        near(parts, out[k]["total"], 0.5, f"census {year} {k} age groups")
    return out


def census(pop: dict, lfs: dict) -> None:
    c = {y: census_year(y) for y in (2020, 2025)}
    foreign = {y: c[y]["all"]["total"] - c[y]["japanese"]["total"] for y in c}
    near(round(c[2025]["all"]["total"] / 1000), 122_973, 0, "census 2025 total")
    near(round(c[2025]["japanese"]["total"] / 1000), 119_132, 0,
         "census 2025 Japanese")
    near(round(foreign[2025] / 1000), 3_840, 1, "census 2025 foreign")
    near(round((foreign[2025] / foreign[2020] - 1) * 100, 1), 39.8, 0.05,
         "census foreign growth 2020→2025")
    # Second sources: the estimates' 2020 row is the census; the LFS
    # 15+ population of 2025 against the census 15+ (total − under 15).
    near(c[2020]["all"]["total"] / 1000, pop[2020]["total"], 0.6,
         "census 2020 vs population estimates 2020")
    c15 = (c[2025]["all"]["total"] - c[2025]["all"]["age_0_14"]) / 1000
    if abs(c15 / lfs["pop15_2025_k"] - 1) > 0.01:
        raise RuntimeError(f"census 2025 aged 15+ {c15:,.0f}k vs LFS "
                           f"{lfs['pop15_2025_k']:,.0f}k")
    print(f"  cross-check: census 2025 aged 15+ {c15:,.0f}k vs LFS 2025 "
          f"{lfs['pop15_2025_k']:,.0f}k")
    write("demography/census_from_stat.csv", """
Statistics Bureau of Japan (MIC), Population Census (国勢調査) on 1
October, PERSONS (not thousands). Basic tabulation table 2-3, the
IMPUTED reference tables (不詳補完値: unknown nationality and age
assigned statistically) of the 2025 census release, for 2025 and for
2020 re-tabulated on the same method. These are the figures of the
official summary (2025: 122,973k / Japanese 119,132k / foreign 3,840k);
the raw tables leave unknowns unassigned and give a smaller Japanese
count. foreign = total - japanese, COMPUTED here. Age groups are the
published 0-14 / 15-64 / 65+ counts. The census is the benchmark the
population estimates will be re-based on; it is a different series
from population_from_stat.csv and the two are never spliced.
""", ["census_year", "population", "japanese", "foreign", "age_0_14",
      "age_15_64", "age_65plus", "japanese_age_65plus"],
          [[y, fmt(c[y]["all"]["total"], 0), fmt(c[y]["japanese"]["total"], 0),
            fmt(foreign[y], 0), fmt(c[y]["all"]["age_0_14"], 0),
            fmt(c[y]["all"]["age_15_64"], 0), fmt(c[y]["all"]["age_65plus"], 0),
            fmt(c[y]["japanese"]["age_65plus"], 0)] for y in sorted(c)])


def main() -> None:
    print("Statistics Bureau of Japan — e-Stat files and stat.go.jp")
    cpi()
    lfs = labour()
    pop = population()
    census(pop, lfs)
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
