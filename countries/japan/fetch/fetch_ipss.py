#!/usr/bin/env python3
"""Refresh the IPSS national population projection.

Usage:  python3 -I countries/japan/fetch/fetch_ipss.py

The National Institute of Population and Social Security Research
(国立社会保障・人口問題研究所, IPSS) publishes 日本の将来推計人口 roughly every
five years, each based on the latest census. The current vintage is the
2023 projection (令和5年推計), 2020-census base, 2021–2070, with a
reference extension to 2120 (参考推計, not drawn here).

The edition is resolved from IPSS's projection menu (Mainmenu.asp) and the
tables from the edition's own pages, by their titles: the result
comparison page (推計結果比較表, 表10-N, all nine variants side by side) and
the assumption tables (仮定値表, 表1 TFR). Nothing is hardcoded but the menu.

Things this source will mislead you about.

**It is a projection, not data.** Every value after 2020 is a scenario;
the sidecar's `kind` column says `base` for 2020 (the census itself) and
`projection` after, and the plate must say so on every card.

**There are nine variants, not one.** Three fertility assumptions (中位/
高位/低位) times three mortality assumptions, one migration assumption.
The medium-fertility, medium-mortality variant is the headline; the
fertility spread is the honest error bar, the mortality spread is narrow.
All nine total-population lines are kept as columns, never averaged.

**The population is everyone resident, foreigners included** (日本における
外国人を含む, ≥3 months' residence, like the Statistics Bureau and unlike
MHLW's vital statistics, which count Japanese nationals only). Projected
births here therefore include births to foreign parents and run above
MHLW's births for the same year; compare like with like.

**The TFR assumption is on the vital-statistics definition** (人口動態調査と
同定義), so it is comparable with MHLW's published TFR — and reality has
been running below the medium path since the projection was made.

**One vintage per line.** A 2025-census-based projection will supersede
this one; it is a new set of columns or a new file, never spliced onto
this one. The fetcher refuses to run on a different edition until its
spot values are updated.

Spot values (base year = 2020 census 126,146k; 2070 medium 87.0mn, 65+
share 38.7%, TFR 1.36 — the IPSS press-release headlines) are asserted,
and the magnitude is cross-checked against the Statistics Bureau's
population estimates and the World Bank's population series.

Needs openpyxl and poppler's `pdftotext` (Statistics Bureau cross-check).

Outputs are `_from_ipss.csv` sidecars. Nothing here overwrites a curated
file.
"""
from __future__ import annotations

import csv
import io
import json
import re
import shutil
import subprocess
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
    raise SystemExit("openpyxl is required (pip install -r "
                     "requirements-fetch.txt); refusing to skip the xlsx "
                     "sources silently.")

warnings.filterwarnings("ignore", module="openpyxl")

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache"

IPSS = "https://www.ipss.go.jp"
MENU = IPSS + "/syoushika/tohkei/Mainmenu.asp"
EDITION_PAGE = IPSS + "/pp-zenkoku/j/zenkoku{ed}/pp_zenkoku{ed}.asp"
STAT_EDITIONS = "https://www.stat.go.jp/data/jinsui/2.html"
WB_POP = ("https://api.worldbank.org/v2/country/JPN/indicator/SP.POP.TOTL"
          "?format=json&date=2015:2026&per_page=100")

EDITION = 2023               # the vintage the spot values below belong to
# IPSS 令和5年推計 press release: base 126,146k (2020 census, 不詳補完);
# medium variant 2070 total 8,700万 (86,996k), 65+ 38.7%, TFR 1.36.
SPOT = {("pop", "fmed_mmed", 2020): (126146.099, 0.001),
        ("pop", "fmed_mmed", 2070): (86996.009, 0.001),
        ("share65", "fmed_mmed", 2070): (38.7, 0.001),
        ("tfr", "fmed", 2070): (1.3573, 0.00005)}

FERT = {"出生中位": "fmed", "出生高位": "fhigh", "出生低位": "flow"}
MORT = {"死亡中位仮定": "mmed", "死亡高位仮定": "mhigh", "死亡低位仮定": "mlow"}
# Comparison tables wanted: normalised title -> (prefix, variants kept).
TABLES = {
    "表10-1総人口": ("pop", None),
    "表10-7 65歳以上人口割合(総人口)".replace(" ", ""): (
        "share65", ["fmed_mmed", "fhigh_mmed", "flow_mmed"]),
    "表10-12出生数(総人口)": ("births", ["fmed_mmed", "fhigh_mmed",
                                       "flow_mmed"]),
    "表10-13死亡数(総人口)": ("deaths", ["fmed_mmed", "fmed_mhigh",
                                       "fmed_mlow"]),
}
TFR_TITLE = "表1合計特殊出生率の推移"

_last_request = 0.0
HTML, XLSX, PDF = (b"<",), (b"PK",), (b"%PDF",)


def fetch(url: str, name: str, magic: tuple[bytes, ...]) -> bytes:
    """One payload, shape-checked BEFORE caching, with polite retries."""
    global _last_request
    CACHE.mkdir(exist_ok=True)
    local = CACHE / name
    if local.exists():
        return local.read_bytes()
    last = None
    for attempt in range(5):
        wait = 1.5 - (time.time() - _last_request)
        if wait > 0:
            time.sleep(wait)
        _last_request = time.time()
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "worldreports-fetch"})
            with urllib.request.urlopen(req, timeout=180) as r:
                blob = r.read()
            head = blob.lstrip()[:16].lower()
            if not any(head.startswith(m.lower()) for m in magic):
                raise ValueError(f"payload starts {blob[:16]!r}, expected "
                                 f"{magic} (error page?)")
            if magic == XLSX:
                zipfile.ZipFile(io.BytesIO(blob)).testzip()
            local.write_bytes(blob)
            return blob
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 404:
                raise
            time.sleep(30 * (attempt + 1) if e.code in (403, 429)
                       else 3 * (attempt + 1))
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"{url}: {last}")


def page(url: str, name: str) -> str:
    blob = fetch(url, name, HTML)
    try:
        return blob.decode("utf-8")
    except UnicodeDecodeError:
        return blob.decode("cp932", errors="replace")


def norm(cell) -> str:
    if cell is None:
        return ""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(cell)))


def num(cell) -> float | None:
    try:
        return float(norm(cell).replace(",", ""))
    except ValueError:
        return None


def items(base: str, html: str) -> list[tuple[str, str]]:
    """(normalised visible text, absolute url) of each link-bearing <li>,
    comments stripped (IPSS leaves commented-out HTML links in place)."""
    html = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    out = []
    for li in re.findall(r"<li>(.*?)</li>", html, re.S):
        for href in re.findall(r'href="([^"]+)"', li):
            out.append((norm(re.sub(r"<[^>]+>", "", li)),
                        urllib.parse.urljoin(base, href)))
    return out


def workbook(url: str, name: str) -> list[list]:
    fetch(url, name, XLSX)
    wb = openpyxl.load_workbook(CACHE / name, read_only=True, data_only=True)
    rows = [list(r) for r in wb.worksheets[0].iter_rows(values_only=True)]
    wb.close()
    return rows


def year_rows(rows: list[list]):
    """(year, row) for data rows: col B the Gregorian year, col A the
    Reiwa year (era written once); both must agree."""
    for r in rows:
        if len(r) < 3 or not isinstance(r[1], (int, float)):
            continue
        year = int(r[1])
        if not 1900 < year < 2200:
            continue
        m = re.fullmatch(r"(令和)?(\d+)", norm(r[0]))
        if m and 2018 + int(m.group(2)) != year:
            raise RuntimeError(f"IPSS table: {r[0]!r} is not {year}")
        yield year, r


def comparison(rows: list[list]) -> dict[str, dict[int, float]]:
    """variant ('fmed_mmed' …) -> {year: value} from a 表10-N sheet."""
    mort_row = next(r for r in rows[:6] if any(norm(c) in MORT for c in r))
    fert_row = rows[rows.index(mort_row) + 1]
    cols, mort = {}, None
    for j, c in enumerate(fert_row):
        if norm(mort_row[j]) in MORT:
            mort = MORT[norm(mort_row[j])]
        if norm(c) in FERT and mort:
            cols[j] = f"{FERT[norm(c)]}_{mort}"
    if len(cols) != 9:
        raise RuntimeError(f"IPSS comparison: {len(cols)} variant columns")
    out: dict[str, dict[int, float]] = {v: {} for v in cols.values()}
    for year, r in year_rows(rows):
        for j, v in cols.items():
            out[v][year] = num(r[j])
    return out


def tfr_table(rows: list[list]) -> dict[str, dict[int, float]]:
    hdr = next(r for r in rows[:6] if "中位" in [norm(c) for c in r])
    cols = {j: {"中位": "fmed", "高位": "fhigh", "低位": "flow"}[norm(c)]
            for j, c in enumerate(hdr) if norm(c) in ("中位", "高位", "低位")}
    out: dict[str, dict[int, float]] = {v: {} for v in cols.values()}
    for year, r in year_rows(rows):
        for j, v in cols.items():
            out[v][year] = num(r[j])
    return out


def stat_bureau_population() -> dict[int, int]:
    """Statistics Bureau 1 October population, THOUSANDS (all residents),
    from the newest annual 人口推計 edition's 結果の概要 PDF, table 2."""
    html = page(STAT_EDITIONS, "ipss_xcheck_stat_jinsui_list.html")
    eds = sorted(set(re.findall(r"/data/jinsui/(\d{4})np/", html)))
    if not eds:
        raise RuntimeError("Statistics Bureau: no annual editions listed")
    ed = eds[-1]
    base = f"https://www.stat.go.jp/data/jinsui/{ed}np/index.html"
    pdfs = re.findall(r'href="([^"]+gaiyou\.pdf)"',
                      page(base, f"ipss_xcheck_stat_{ed}np.html"))
    if not pdfs:
        raise RuntimeError(f"Statistics Bureau {ed}np: no gaiyou.pdf")
    name = f"ipss_xcheck_stat_{ed}gaiyou.pdf"
    fetch(urllib.parse.urljoin(base, pdfs[0]), name, PDF)
    if not shutil.which("pdftotext"):
        raise SystemExit("pdftotext (poppler) is required for the "
                         "Statistics Bureau cross-check.")
    text = subprocess.run(["pdftotext", "-layout", str(CACHE / name), "-"],
                          check=True, capture_output=True, text=True).stdout
    out = {}
    for m in re.finditer(r"^\s*(\d{4})年?\s+([\d,]{7})\b", text, re.M):
        pop = int(m.group(2).replace(",", ""))
        if pop > 100_000:            # table 2 rows only (thousands)
            out.setdefault(int(m.group(1)), pop)
    if len(out) < 10:
        raise RuntimeError("Statistics Bureau gaiyou: table 2 not parsed")
    return out


def world_bank_population() -> dict[int, float]:
    payload = json.loads(fetch(WB_POP, "ipss_xcheck_wb_SP.POP.TOTL.json",
                               (b"[",)))
    if len(payload) < 2 or not payload[1]:
        raise RuntimeError("World Bank SP.POP.TOTL: empty payload")
    return {int(r["date"]): r["value"] for r in payload[1]
            if r["value"] is not None}


def main() -> None:
    print("IPSS")
    menu = page(MENU, "ipss_mainmenu.html")
    eds = sorted({int(e) for e in re.findall(r"zenkoku(\d{4})", menu)})
    if not eds:
        raise RuntimeError("IPSS menu: no national projection listed")
    ed = eds[-1]
    if ed != EDITION:
        raise SystemExit(f"  !! IPSS now lists the {ed} projection; this "
                         f"fetcher's spot values are for {EDITION}. A new "
                         f"vintage is a new line, never spliced: update "
                         f"SPOT and the comments first.")
    print(f"  projection: {ed} (令和{ed - 2018}年推計)")

    top = EDITION_PAGE.format(ed=ed)
    detail = next((u for t, u in items(top, page(top, f"ipss_pp{ed}.html"))
                   if "syosaikekka" in u), None)
    if detail is None:
        # The detailed-results link sits in a <p>, not an <li>.
        m = re.search(r'href="([^"]*syosaikekka[^"]*\.html)"',
                      page(top, f"ipss_pp{ed}.html"))
        if not m:
            raise RuntimeError("IPSS: no detailed-results page")
        detail = urllib.parse.urljoin(top, m.group(1))
    dl = items(detail, page(detail, f"ipss_pp{ed}_detail.html"))
    comp = next((u for t, u in dl if "推計結果比較表" in t), None)
    tfr_url = next((u for t, u in dl if t.startswith(TFR_TITLE)
                    and u.endswith(".xlsx")), None)
    if not comp or not tfr_url:
        raise RuntimeError("IPSS: comparison page or 表1 TFR not found")
    tables = {t: u for t, u in items(comp, page(comp, f"ipss_pp{ed}_"
                                                      "compare.html"))
              if u.endswith(".xlsx")}

    series: dict[str, dict[int, float]] = {}
    for title, (prefix, keep) in TABLES.items():
        url = next((u for t, u in tables.items() if t.startswith(title)),
                   None)
        if url is None:
            raise RuntimeError(f"IPSS: comparison table {title} not found")
        rows = workbook(url, f"ipss_pp{ed}_{url.rsplit('/', 1)[-1]}")
        if not norm(rows[1][0] if rows[1] else "").startswith(
                title.split("(")[0][:6]):
            raise RuntimeError(f"IPSS {title}: sheet title is {rows[1][0]!r}")
        for v, vals in comparison(rows).items():
            if keep is None or v in keep:
                series[f"{prefix}_{v}"] = vals
    tfr = tfr_table(workbook(tfr_url, f"ipss_pp{ed}_"
                                      f"{tfr_url.rsplit('/', 1)[-1]}"))
    for v, vals in tfr.items():
        series[f"tfr_{v}"] = vals

    for (prefix, v, y), (want, tol) in SPOT.items():
        got = series[f"{prefix}_{v}"].get(y)
        if got is None or abs(got - want) > tol:
            raise SystemExit(f"  !! {prefix}_{v} {y} = {got}, published "
                             f"{want}; not writing")
        print(f"  ok {prefix}_{v} {y}: {got} (published {want})")
    # The nine variants share the 2020 census base exactly.
    base = {series[f"pop_{f}_{m}"][2020] for f in FERT.values()
            for m in MORT.values()}
    if len(base) != 1:
        raise SystemExit(f"  !! 2020 base differs across variants: {base}")

    # Cross-check 1: the base year IS the 2020 census as the Statistics
    # Bureau publishes it, and the medium path sits close to the Bureau's
    # own estimates for the years since (estimates still on the 2020
    # base, so this measures the projection, not a re-basing).
    sb = stat_bureau_population()
    med = series["pop_fmed_mmed"]
    if abs(sb[2020] - med[2020]) > 1:
        raise SystemExit(f"  !! 2020: Statistics Bureau {sb[2020]:,}k vs "
                         f"IPSS base {med[2020]:,}k")
    print(f"  ok 2020 base vs Statistics Bureau census: {sb[2020]:,}k")
    for y in sorted(y for y in sb if 2021 <= y in med):
        gap = med[y] / sb[y] - 1
        if abs(gap) > 0.01:
            raise SystemExit(f"  !! {y}: IPSS medium {med[y]:,.0f}k vs "
                             f"Statistics Bureau {sb[y]:,}k ({gap:+.2%})")
        print(f"  ok {y} IPSS medium vs Statistics Bureau estimate: "
              f"{gap:+.2%}")
    # Cross-check 2: World Bank mid-year population (UN/national) within
    # 1.5% of the 1 October projection.
    wb = world_bank_population()
    for y in (2022, 2024):
        gap = med[y] * 1000 / wb[y] - 1
        if abs(gap) > 0.015:
            raise SystemExit(f"  !! {y}: IPSS medium vs World Bank "
                             f"{gap:+.2%}")
        print(f"  ok {y} IPSS medium vs World Bank population: {gap:+.2%}")

    header = (["year", "kind"]
              + [f"pop_{f}_{m}" for m in MORT.values() for f in FERT.values()]
              + [k for k in series if not k.startswith("pop_")])
    years = sorted(med)
    rows = [[y, "base" if y == 2020 else "projection"]
            + [series[k].get(y) for k in header[2:]] for y in years]
    path = DATA / "demography" / "projection_from_ipss.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    comment = f"""
IPSS Population Projections for Japan ({ed}; 令和{ed - 2018}年推計), 2020-census
base, 2021-2070 (the 2071-2120 reference extension is not included). 1
October each year. kind = base for 2020 (the census, 不詳補完 imputed),
projection after: SCENARIOS, NOT DATA. Variant suffix: f = fertility
assumption, m = mortality assumption (med/high/low); fmed_mmed is the
headline. One migration assumption throughout. pop_* = total population,
THOUSANDS (1,000 persons), all residents INCLUDING FOREIGNERS (unlike MHLW
vital statistics, Japanese nationals only). share65_* = % aged 65+.
births_*/deaths_* = THOUSANDS of events in the calendar year (1 Jan-31 Dec,
per IPSS 表1-8), total population incl. births to foreign parents, so
above MHLW's Japanese-only births; 2021 onward are projected, not actual.
tfr_* = assumed total fertility rate on the vital-statistics definition
(comparable with MHLW's TFR), mortality medium; 2020 is the actual rate.
One vintage per line: a 2025-census-based projection supersedes this as
new columns or a new file, never spliced."""
    with path.open("w", newline="", encoding="utf-8") as fh:
        for line in comment.strip().splitlines():
            fh.write(f"# {line}".rstrip() + "\n")
        w = csv.writer(fh)
        w.writerow(header)
        for r in rows:
            w.writerow(["" if v is None else v for v in r])
    print(f"  -> data/demography/projection_from_ipss.csv  {len(rows)} rows "
          f"({years[0]}–{years[-1]}, {len(header) - 2} series)")

    print("Done. Diff the sidecar before adopting.")


if __name__ == "__main__":
    main()
