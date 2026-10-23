#!/usr/bin/env python3
"""Refresh the Ministry of Health, Labour and Welfare (MHLW) series.

Usage:  python3 -I countries/japan/fetch/fetch_mhlw.py

Four MHLW products, each resolved from the ministry's own index pages at
fetch time (file names churn between editions, so none is hardcoded):

  * Vital Statistics, final figures (人口動態統計 確定数): births, deaths,
    natural change, infant deaths, marriages, divorces, crude rates and
    the total fertility rate. The edition list is /toukei/list/81-1a.html;
    the newest edition's 第2表/第3表 (人口動態総覧の年次推移) carry the
    whole annual series back to 1899, already revised.
  * Causes of death (第N表 死因簡単分類別にみた性別死亡数), one edition per
    year. The table number moves (第7表 → 第9表 → 第8表) and so does the
    file (hyo.xls, 02.xls in 2008, hyo.xlsx, 16_hyoR06.xlsx, 06_hyoR07.xlsx),
    so the sheet is found by its title, never by its number.
  * Abridged life tables (簡易生命表), edition list
    /toukei/saikin/hw/seimei/list54-57-02.html.
  * Comprehensive Survey of Living Conditions (国民生活基礎調査), edition
    list /toukei/list/20-21kekka.html: the relative-poverty table.

Things this source will mislead you about.

**Vital statistics count JAPANESE NATIONALS IN JAPAN (日本における日本人).**
Births to two foreign parents, and deaths of foreign residents, are not in
these numbers (MHLW publishes them separately in 別表). The rates use the
Japanese population as the denominator. This is a different population
from the Statistics Bureau's total-population estimates, which include
~3.8mn foreign residents: the Bureau's own births line runs several per
cent above MHLW's. The fetcher checks that gap rather than hiding it.

**Old editions were revised in 2019 and the old files were not.** On
2019-03-29 MHLW re-tabulated 2004, 2006 and 2009–2017 after prefectures
were found to have under-reported (都道府県からの報告漏れ). The 第2表 long
series carries the revised totals; the per-year cause-of-death editions
for those years are the ORIGINAL tabulation (2006 all-cause 1,084,450 in
its edition vs 1,084,451 revised). The causes sidecar therefore carries
both totals in two columns, `all_causes` (the edition's own) and
`all_causes_revised` (第2表), and the gap is written into the comments.

**The cause list changes under the reader in 2017.** Japan adopted the
ICD-10 (2013 version) for 2017 deaths, and the 死因簡単分類 gained 10601
aspiration pneumonia (誤嚥性肺炎), split out of 10200 pneumonia — which
drops by ~22,000 that year for coding reasons alone. Aspiration
pneumonia is its own column, blank before 2017, never added back.

**COVID-19 has two codes.** For 2020–2022 the editions publish only
22200 その他の特殊目的用コード (the special-purpose U-codes, i.e. U07
COVID-19 in practice); from the 2023 edition 22201 新型コロナウイルス感染症
is split out. Two columns, never joined.

**"Senility" (老衰, 18100) is a certified underlying cause** that Japanese
doctors use far more than most countries, and it has risen from ~28k to
~215k inside the window. It is a column like any other here; the plate
must say what it is.

**Symbols.** MHLW writes "-" for a count of zero (計数のない場合), "…" for
not available and "・" for not applicable. "-" becomes 0; the other two
become blank. A cause code absent from an edition is blank.

**Life tables come in two kinds.** The abridged table (簡易生命表) is
published every year; the complete table (完全生命表) only for census years
(2010, 2015, 2020), and the ministry's own year series uses the complete
value in census years. The two are separate columns here; the abridged
values for census years are read from those years' own abridged editions.

**Poverty is triennial and keyed on the INCOME year.** The 2025 survey
reports incomes of 2024. 2018 exists on two income definitions (旧基準 /
新基準, OECD 2015 terms of reference): two columns, one seam.

Spot values from DISCOVERY.md are asserted before anything is written, and
the deaths and births magnitudes are cross-checked against the Statistics
Bureau's population estimates (人口推計, which take their natural change
from MHLW but count every resident) and the World Bank.

Needs openpyxl, LibreOffice (`soffice`, to read the pre-2019 .xls
editions — openpyxl cannot, and xlrd is not importable under -I) and
poppler's `pdftotext` (for the Statistics Bureau cross-check).

Outputs are `_from_mhlw.csv` sidecars. Nothing here overwrites a curated
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

# The MHLW workbooks trip harmless openpyxl print-area warnings.
warnings.filterwarnings("ignore", module="openpyxl")

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache"

Y0, Y1 = 2006, 2026          # atlas window
MHLW = "https://www.mhlw.go.jp"
VITAL_LIST = MHLW + "/toukei/list/81-1a.html"
LIFE_LIST = MHLW + "/toukei/saikin/hw/seimei/list54-57-02.html"
KTYOSA_LIST = MHLW + "/toukei/list/20-21kekka.html"
STAT_EDITIONS = "https://www.stat.go.jp/data/jinsui/2.html"
WB = ("https://api.worldbank.org/v2/country/JPN/indicator/{code}"
      "?format=json&date=2006:2026&per_page=100")

# Published figures (DISCOVERY.md / MHLW releases) the run must reproduce.
SPOT_VITAL = {2025: {"births": 671270, "deaths": 1589533, "tfr": 1.14,
                     "natural_change": -918263},
              2024: {"births": 686173, "deaths": 1605378, "tfr": 1.15},
              2006: {"births": 1092674, "tfr": 1.32}}
SPOT_CAUSES = {2025: {"02100": 378829, "09200": 220539, "18100": 214712,
                      "09300": 100361, "10200": 84021, "20100": 45068,
                      "20200": 18537, "20300": 211, "22201": 21496},
               2024: {"20300": 222, "22201": 35865}}
SPOT_LIFE = {2025: (81.35, 87.33)}
SPOT_POVERTY = {2024: {"poverty_rate_new": 15.0, "child_poverty_new": 11.0},
                2018: {"poverty_rate_old": 15.4, "poverty_rate_new": 15.7}}

# Abridged causes drawn as columns: code -> column name.
CAUSES = {
    "02100": "malignant_neoplasms_02100",
    "09200": "heart_disease_09200",
    "09300": "cerebrovascular_09300",
    "10200": "pneumonia_10200",
    "10601": "aspiration_pneumonia_10601",
    "18100": "senility_18100",
    "20100": "accidents_20100",
    "20200": "suicide_20200",
    "20300": "homicide_20300",
    "14200": "renal_failure_14200",
    "06400": "alzheimers_06400",
    "05100": "vascular_dementia_05100",
    "22200": "special_purpose_codes_22200",
    "22201": "covid19_22201",
}

ERAS = {"明治": 1867, "大正": 1911, "昭和": 1925, "平成": 1988, "令和": 2018}

_last_request = 0.0


# ---------------------------------------------------------------- network

def fetch(url: str, name: str, magic: tuple[bytes, ...]) -> bytes:
    """One payload, shape-checked BEFORE caching, with polite retries.

    `magic` lists acceptable leading bytes: PK (xlsx zip), the OLE2
    header (xls), %PDF, '<' (html) or '[' (World Bank JSON). An HTML error
    page served under HTTP 200 never lands in the cache.
    """
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
            if magic == (b"PK",):
                zipfile.ZipFile(io.BytesIO(blob)).testzip()
            local.write_bytes(blob)
            return blob
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 404:
                raise
            # Back off hard on rate limits and walls.
            time.sleep(30 * (attempt + 1) if e.code in (403, 429)
                       else 3 * (attempt + 1))
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"{url}: {last}")


HTML = (b"<",)
XLSX = (b"PK",)
XLS = (b"\xd0\xcf\x11\xe0",)
PDF = (b"%PDF",)


def page(url: str, name: str) -> str:
    """An HTML page decoded explicitly: MHLW/Stat pages are mostly cp932."""
    blob = fetch(url, name, HTML)
    try:
        return blob.decode("utf-8")
    except UnicodeDecodeError:
        return blob.decode("cp932", errors="replace")


def links(base: str, html: str, pattern: str) -> list[tuple[str, str]]:
    """(absolute url, link text) for hrefs matching `pattern`, page order."""
    out = []
    for href, text in re.findall(r'href="([^"]+)"[^>]*>(.*?)</a>', html,
                                 re.S):
        if re.search(pattern, href):
            text = re.sub(r"<[^>]+>", "", text)
            out.append((urllib.parse.urljoin(base, href), norm(text)))
    return out


def editions(list_url: str, name: str, pattern: str) -> list[int]:
    """Two-digit edition codes on a list page -> calendar years, newest
    first (codes ≥ 90 are 19xx: kakutei95 is 1995)."""
    html = page(list_url, name)
    codes = {int(c) for c in re.findall(pattern, html)}
    if not codes:
        raise RuntimeError(f"{list_url}: no editions matching {pattern}")
    return sorted(((1900 if c >= 90 else 2000) + c for c in codes),
                  reverse=True)


# --------------------------------------------------------------- workbooks

def sheets(path: Path) -> list[tuple[str, list[list]]]:
    """Every sheet of an xlsx, or of an xls converted to xlsx by soffice."""
    if path.suffix == ".xls":
        path = xls_to_xlsx(path)
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    out = [(ws.title, [list(r) for r in ws.iter_rows(values_only=True)])
           for ws in wb.worksheets]
    wb.close()
    return out


def xls_to_xlsx(path: Path) -> Path:
    """Convert a BIFF .xls with headless LibreOffice, into the cache.

    A private profile directory keeps a running LibreOffice from
    swallowing the job; the result is shape-checked like a download.
    """
    target = path.with_suffix(".xlsx")
    if target.exists():
        return target
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise SystemExit("LibreOffice (soffice) is required to read the "
                         "pre-2019 MHLW .xls editions; refusing to skip "
                         "them silently.")
    profile = (CACHE / "mhlw_soffice_profile").resolve()
    subprocess.run([soffice, f"-env:UserInstallation=file://{profile}",
                    "--headless", "--norestore", "--convert-to", "xlsx",
                    "--outdir", str(CACHE.resolve()), str(path.resolve())],
                   check=True, capture_output=True, timeout=300)
    if not target.exists() or target.read_bytes()[:2] != b"PK":
        raise RuntimeError(f"soffice did not convert {path.name}")
    return target


def norm(cell) -> str:
    """NFKC (full-width digits to ASCII) with all whitespace removed."""
    if cell is None:
        return ""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(cell)))


def count(cell) -> int | None:
    """MHLW count: '-' is a true zero, '…'/'・'/blank are holes."""
    t = norm(cell).replace(",", "")
    if t in ("-", "−", "‐", "―"):
        return 0
    try:
        return int(round(float(t)))
    except ValueError:
        return None


def rate(cell) -> float | None:
    t = norm(cell).replace(",", "")
    try:
        return float(t)
    except ValueError:
        return None


def wareki(label: str) -> int | None:
    """'平成18年', '令和7年(2025)', '令和元' -> Gregorian year, or None."""
    t = norm(label)
    m = re.search(r"(明治|大正|昭和|平成|令和)(元|\d+)", t)
    if not m:
        return None
    n = 1 if m.group(2) == "元" else int(m.group(2))
    year = ERAS[m.group(1)] + n
    g = re.search(r"\((\d{4})\)", t)
    if g and int(g.group(1)) != year:
        raise RuntimeError(f"wareki {label!r}: {year} vs {g.group(1)}")
    return year


assert_known = [("平成18年", 2006), ("令和元", 2019), ("令和7年(2025)", 2025),
                ("昭和22", 1947)]
for _label, _year in assert_known:
    if wareki(_label) != _year:
        raise SystemExit(f"wareki table broken: {_label} -> "
                         f"{wareki(_label)}, expected {_year}")


def check(label: str, got, want, tol: float) -> None:
    """Raise unless |got - want| <= tol (absolute)."""
    if got is None:
        raise SystemExit(f"  !! {label}: missing from the data")
    if abs(got - want) > tol:
        raise SystemExit(f"  !! {label} = {got:,}, published {want:,}; "
                         f"not writing")
    print(f"  ok {label}: {got:,} (published {want:,})")


def write(rel: str, comment: str, header: list[str], rows: list[list]
          ) -> None:
    path = DATA / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        for line in comment.strip().splitlines():
            fh.write(f"# {line}".rstrip() + "\n")
        w = csv.writer(fh)
        w.writerow(header)
        for r in rows:
            w.writerow(["" if v is None else v for v in r])
    span = f"{rows[0][0]}–{rows[-1][0]}" if rows else "empty"
    print(f"  -> data/{rel}  {len(rows)} rows ({span})")


# ---------------------------------------------------------- vital editions

def vital_edition(year: int) -> tuple[str, list[tuple[str, str]]]:
    """(index url, excel links) of the kakuteiNN edition for `year`."""
    yy = f"{year % 100:02d}"
    url = f"{MHLW}/toukei/saikin/hw/jinkou/kakutei{yy}/index.html"
    html = page(url, f"mhlw_kakutei{yy}_index.html")
    return url, links(url, html, r"\.xlsx?$")


def edition_workbook(year: int, wanted: str) -> list[tuple[str, list[list]]]:
    """Sheets of the year's statistical-table workbook holding `wanted`.

    The index links several workbooks (the tables, a list of tables, the
    prefectural ranking, chart data); the candidates are tried in page
    order, skipping the ones whose names say they are not the tables,
    until one carries a sheet whose title contains `wanted`.
    """
    yy = f"{year % 100:02d}"
    _, cands = vital_edition(year)
    skip = re.compile(r"toukei|sankou|itiran|zu", re.I)
    seen = set()
    for url, _text in cands:
        fname = url.rsplit("/", 1)[-1]
        if skip.search(fname) or url in seen:
            continue
        seen.add(url)
        ext = Path(fname).suffix
        local = CACHE / f"mhlw_kakutei{yy}_{Path(fname).stem}{ext}"
        fetch(url, local.name, XLS if ext == ".xls" else XLSX)
        found = sheets(local)
        if any(wanted in title_text(rows) for _, rows in found):
            return found
    raise RuntimeError(f"kakutei{yy}: no workbook with a '{wanted}' sheet")


def title_text(rows: list[list], n: int = 4) -> str:
    return "".join(norm(c) for r in rows[:n] for c in r)


# ------------------------------------------------------------------ vital

def long_series(found, need=("births", "deaths", "tfr")
                ) -> tuple[dict, dict]:
    """第2表 counts and 第3表 rates by year, from the edition's 年次推移.

    Editions split the table over several sheets differently (the 2024
    edition puts marriages on a separate sheet from births), so each
    sheet contributes whichever wanted columns it carries, matched on the
    header label with its unit and footnote marker stripped; a field read
    twice must agree. Every field in `need` must be found.
    """
    counts: dict[int, dict] = {}
    rates: dict[int, dict] = {}
    want2 = {"出生数": "births", "死亡数": "deaths",
             "乳児死亡数": "infant_deaths", "自然増減数": "natural_change",
             "婚姻件数": "marriages", "離婚件数": "divorces"}
    want3 = {"出生率": "birth_rate", "死亡率": "death_rate",
             "乳児死亡率": "infant_mortality_rate",
             "自然増減率": "natural_change_rate", "合計特殊出生率": "tfr"}
    for _, rows in found:
        t = title_text(rows, 2)
        if "人口動態総覧の年次推移" in t:
            target, want, conv = counts, want2, count
        elif "人口動態総覧(率)の年次推移" in t:
            target, want, conv = rates, want3, rate
        else:
            continue
        cols = {}
        for r in rows[2:8]:
            for j, c in enumerate(r):
                label = re.sub(r"(\d\))?(\([^)]*\))?$", "", norm(c))
                if label in want and want[label] not in cols.values():
                    cols[j] = want[label]
        for year, r in years_of(rows):
            rec = target.setdefault(year, {})
            for j, name in cols.items():
                val = conv(r[j])
                if name in rec and rec[name] != val:
                    raise RuntimeError(f"long series {year} {name}: "
                                       f"sheets differ")
                rec[name] = val
    have = {k for d in (counts, rates) for rec in d.values() for k in rec}
    missing = set(need) - have
    if missing:
        raise RuntimeError(f"long series: {sorted(missing)} not found")
    return counts, rates


def years_of(rows: list[list]):
    """(year, row) for the data rows of a 年次推移 sheet.

    Column B is the Gregorian year written in full only at decades (1970,
    71, 72, …, 2000, 1, 2, …); column C the wareki year with the era
    written once (昭和45, 46, …, 平成元, 2, …). Both are decoded and must
    agree, so a skipped row (1944–46 are omitted) cannot shift the years.
    """
    greg = era = None
    for r in rows:
        if len(r) < 4:
            continue
        b, c = r[1], norm(r[2])
        if not isinstance(b, (int, float)) or not c:
            continue
        b = int(b)
        if b >= 1000:
            greg = b
        elif greg is None:
            continue
        else:
            cand = greg - greg % 100 + b
            greg = cand + 100 if cand <= greg else cand
        m = re.match(r"(明治|大正|昭和|平成|令和)?(元|\d+)年?$", c)
        if not m:
            raise RuntimeError(f"long series: wareki cell {r[2]!r}")
        era = m.group(1) or era
        n = 1 if m.group(2) == "元" else int(m.group(2))
        if ERAS[era] + n != greg:
            raise RuntimeError(f"long series: {greg} vs {era}{n}")
        yield greg, r


def vital(latest: int, found_latest, found_prev) -> dict[int, dict]:
    counts, rates = long_series(found_latest, need=(
        "births", "deaths", "natural_change", "infant_deaths", "marriages",
        "divorces", "birth_rate", "death_rate", "infant_mortality_rate",
        "natural_change_rate", "tfr"))
    # Revision check: the previous edition's long series must agree with
    # this one on every shared year within 0.5% (the 2019 recount is
    # already in both).
    pc, _ = long_series(found_prev, need=("births", "deaths"))
    worst = 0.0
    for y in range(Y0, latest):
        for k in ("births", "deaths"):
            a, b = counts[y][k], pc.get(y, {}).get(k)
            if b:
                worst = max(worst, abs(a - b) / b)
    if worst > 0.005:
        raise SystemExit(f"  !! long series revised by {worst:.2%} between "
                         f"editions; diff before adopting")
    print(f"  ok editions {latest} vs {latest - 1}: largest revision on "
          f"births/deaths {worst:.3%}")
    out = {y: {**counts[y], **rates.get(y, {})}
           for y in range(Y0, Y1 + 1) if y in counts}
    for y, spot in SPOT_VITAL.items():
        for k, v in spot.items():
            check(f"{y} {k}", out[y][k], v, 0.005 if k == "tfr" else 0)
    return out


# ----------------------------------------------------------------- causes

CAUSE_TITLE = "死因簡単分類別にみた性別死亡数"


def causes_of(year: int, found) -> dict[str, tuple]:
    """code -> (total, male, female) from the year's own edition.

    The sheet is located by title. The header row naming the year (in
    wareki) must name THIS year; the first three numeric columns after the
    cause name are 総数/男/女 of the death counts (the 2025 edition adds a
    previous-year total in a later column, ignored here).
    """
    out: dict[str, tuple] = {}
    for _, rows in found:
        if CAUSE_TITLE not in title_text(rows, 3):
            continue
        labelled = [wareki(c) for r in rows[:8] for c in r
                    if wareki(c) is not None]
        if not labelled or labelled[0] != year:
            raise RuntimeError(f"causes {year}: sheet is for {labelled[:1]}")
        hdr = next((r for r in rows[:9]
                    if [norm(c) for c in r[3:6]] == ["総数", "男", "女"]),
                   None)
        if hdr is None:
            raise RuntimeError(f"causes {year}: no 総数/男/女 header")
        for r in rows:
            code = norm(r[1]) if len(r) > 5 else ""
            name = norm(r[2]) if len(r) > 5 else ""
            if re.fullmatch(r"\d{5}", code):
                out[code] = (count(r[3]), count(r[4]), count(r[5]))
            elif name == "総数" and "total" not in out:
                out["total"] = (count(r[3]), count(r[4]), count(r[5]))
    if "total" not in out or "20300" not in out:
        raise RuntimeError(f"causes {year}: '{CAUSE_TITLE}' not parsed")
    # Internal consistency: male + female = total for all causes.
    t, m, f = out["total"]
    if m + f != t:
        raise RuntimeError(f"causes {year}: {m}+{f} != {t}")
    return out


# ------------------------------------------------------------------- life

def life_year_series(latest: int) -> dict[int, dict]:
    """参考資料2 主な年齢の平均余命の年次推移 of the newest life edition."""
    yy = f"{latest % 100:02d}"
    base = f"{MHLW}/toukei/saikin/hw/life/life{yy}/index.html"
    cands = links(base, page(base, f"mhlw_life{yy}_index.html"),
                  r"\.xlsx?$")
    for url, _ in cands:
        fname = url.rsplit("/", 1)[-1]
        ext = Path(fname).suffix
        local = CACHE / f"mhlw_life{yy}_{Path(fname).stem}{ext}"
        fetch(url, local.name, XLS if ext == ".xls" else XLSX)
        for _, rows in sheets(local):
            if "主な年齢の平均余命の年次推移" in title_text(rows, 3):
                return parse_life_series(rows)
    raise RuntimeError(f"life{yy}: no 平均余命の年次推移 sheet")


def parse_life_series(rows) -> dict[int, dict]:
    sex_row = next(r for r in rows[:8] if "男" in [norm(c) for c in r])
    age_row = rows[rows.index(sex_row) + 1]
    sexes = [(j, norm(c)) for j, c in enumerate(sex_row) if norm(c) in
             ("男", "女")]
    cols = {}
    for (j, sex), nxt in zip(sexes, sexes[1:] + [(len(age_row), "")]):
        for k in range(j, nxt[0]):
            age = norm(age_row[k]).replace("歳", "")
            if age in ("0", "65"):
                cols[(("male" if sex == "男" else "female"), age)] = k
    if len(cols) != 4:
        raise RuntimeError(f"life series: columns {cols}")
    out: dict[int, dict] = {}
    greg = era = None
    for r in rows:
        if len(r) < 4:
            continue
        g = norm(r[1])
        m = re.fullmatch(r"(\*?)(\d{2,4})", g)
        if not m:
            continue
        n = int(m.group(2))
        if len(m.group(2)) == 4:
            greg = n
        elif greg is None:
            continue
        else:
            cand = greg - greg % 100 + n
            greg = cand + 100 if cand <= greg else cand
        # The wareki column must agree (era written once, like 第2表).
        wk = norm(r[3]).lstrip("*")
        em = re.match(r"(明治|大正|昭和|平成|令和)?(元|\d+)", wk)
        if em:
            if em.group(1):
                era = em.group(1)
            nn = 1 if em.group(2) == "元" else int(em.group(2))
            if ERAS[era] + nn != greg:
                raise RuntimeError(f"life series: {greg} vs {wk}")
        kind = "complete" if m.group(1) == "*" else "abridged"
        out[greg] = {"kind": kind, **{f"e{a}_{s}": rate(r[k])
                                      for (s, a), k in cols.items()}}
    return out


def abridged_table(year: int) -> dict[str, float]:
    """e0 and e65 by sex from one year's own abridged life table.

    Used for census years, where the year series prints the complete
    table instead. Layouts differ (one block per sheet in 2025, two
    side-by-side blocks before), so blocks are found by their x … lx … ex
    symbol row.
    """
    yy = f"{year % 100:02d}"
    base = f"{MHLW}/toukei/saikin/hw/life/life{yy}/index.html"
    cands = links(base, page(base, f"mhlw_life{yy}_index.html"),
                  r"\.xlsx?$")
    for url in dict.fromkeys(u for u, _ in cands):
        fname = url.rsplit("/", 1)[-1]
        ext = Path(fname).suffix
        local = CACHE / f"mhlw_life{yy}_{Path(fname).stem}{ext}"
        fetch(url, local.name, XLS if ext == ".xls" else XLSX)
        found = sheets(local)
        out = {}
        for title, rows in found:
            t = norm(title) + title_text(rows, 2)
            if "簡易生命表" not in t or not ("(男)" in t or "(女)" in t):
                continue
            sex = "male" if "(男)" in t else "female"
            sym = next((r for r in rows[:8]
                        if [norm(c) for c in r].count("ex") >= 1), None)
            if sym is None:
                continue
            s = [norm(c) for c in sym]
            for j in [i for i, c in enumerate(s) if c == "x"]:
                if "lx" not in s[j:] or "ex" not in s[j:]:
                    continue
                lx = s.index("lx", j)
                ex = s.index("ex", j)
                for r in rows:
                    if len(r) <= ex:
                        continue
                    if f"e0_{sex}" not in out and count(r[lx]) == 100000:
                        out[f"e0_{sex}"] = rate(r[ex])
                    age = norm(r[j]).replace("年", "")
                    unit = norm(r[j + 1]) if j + 1 < len(r) else ""
                    if age in ("65", "65.0") and not re.search(
                            "週|月", unit):
                        out[f"e65_{sex}"] = rate(r[ex])
        if len(out) == 4:
            return out
    raise RuntimeError(f"life{yy}: abridged life table not parsed")


# ---------------------------------------------------------------- poverty

def poverty() -> tuple[int, dict[int, dict], str]:
    """表11 貧困率の年次推移 from the newest large-scale survey edition."""
    for ed in editions(KTYOSA_LIST, "mhlw_ktyosa_list.html",
                       r"k-tyosa/k-tyosa(\d\d)/")[:4]:
        yy = f"{ed % 100:02d}"
        base = f"{MHLW}/toukei/saikin/hw/k-tyosa/k-tyosa{yy}/index.html"
        try:
            html = page(base, f"mhlw_ktyosa{yy}_index.html")
        except urllib.error.HTTPError:
            continue
        for url, text in links(base, html, r"\.xlsx$"):
            if "所得" not in text:
                continue
            fname = url.rsplit("/", 1)[-1]
            local = CACHE / f"mhlw_ktyosa{yy}_{fname}"
            fetch(url, local.name, XLSX)
            for _, rows in sheets(local):
                if re.search(r"表\d+貧困率の年次推移", title_text(rows, 3)):
                    return ed, parse_poverty(rows), url
    raise RuntimeError("Living Conditions Survey: no 貧困率 table found")


def parse_poverty(rows) -> dict[int, dict]:
    """Year labels (income years) and value rows; 2018 has two values.

    There is one more value than labels in each row: the 2018 label covers
    an old-definition and a new-definition value, in that order (the
    旧基準/新基準 row). Up to 2018 old values are 'old', from 2018 new
    ones are 'new'.
    """
    lab = next(r for r in rows if sum(bool(re.match(r"\d{4}", norm(c)))
                                      for c in r) >= 5)
    years = [int(norm(c)[:4]) for c in lab if re.match(r"\d{4}", norm(c))]
    if 2018 not in years:
        raise RuntimeError("poverty table: no 2018 seam")
    names = {"相対的貧困率": "poverty_rate", "子どもの貧困率": "child_poverty",
             "中央値(a)": "median_income", "貧困線(a/2)": "poverty_line"}
    out: dict[int, dict] = {y: {} for y in years}
    for r in rows:
        # The row label sits in one of the first few columns.
        key = next((names[norm(c)] for c in r[:4] if norm(c) in names),
                   None)
        if key is None:
            continue
        vals = [rate(c) for c in r if rate(c) is not None]
        if len(vals) != len(years) + 1:
            raise RuntimeError(f"poverty {key}: {len(vals)} values for "
                               f"{len(years)} labels")
        seam = years.index(2018)
        for i, y in enumerate(years):
            if i < seam:
                out[y][f"{key}_old"] = vals[i]
            elif i == seam:
                out[y][f"{key}_old"] = vals[i]
                out[y][f"{key}_new"] = vals[i + 1]
            else:
                out[y][f"{key}_new"] = vals[i + 1]
    return out


# ------------------------------------------------------------ cross-checks

def stat_bureau_vital() -> dict[int, tuple[int, int]]:
    """Statistics Bureau 人口推計: (births, deaths) in THOUSANDS, total
    population (foreign residents included), October to September — from
    the newest annual edition's 結果の概要 PDF, table 2."""
    html = page(STAT_EDITIONS, "mhlw_xcheck_stat_jinsui_list.html")
    eds = sorted(set(re.findall(r"/data/jinsui/(\d{4})np/", html)))
    if not eds:
        raise RuntimeError("Statistics Bureau: no annual editions listed")
    ed = eds[-1]
    base = f"https://www.stat.go.jp/data/jinsui/{ed}np/index.html"
    pdfs = [u for u, _ in links(base, page(base, f"mhlw_xcheck_stat_{ed}np"
                                                 ".html"), r"gaiyou\.pdf$")]
    if not pdfs:
        raise RuntimeError(f"Statistics Bureau {ed}np: no gaiyou.pdf")
    local = CACHE / f"mhlw_xcheck_stat_{ed}gaiyou.pdf"
    fetch(pdfs[0], local.name, PDF)
    if not shutil.which("pdftotext"):
        raise SystemExit("pdftotext (poppler) is required for the "
                         "Statistics Bureau cross-check.")
    text = subprocess.run(["pdftotext", "-layout", str(local), "-"],
                          check=True, capture_output=True,
                          text=True).stdout
    out = {}
    row = re.compile(r"^\s*(\d{4})年?\s+([\d,]+)\s*(?:\d\))?\s+(-?[\d,]+)\s+"
                     r"(-?[\d.]+)\s+([\d,]+)\s+([\d,]+)\s+(-?[\d,]+)\s")
    for line in text.splitlines():
        m = row.match(line)
        # Table 2 rows only: a total population above 100mn (thousands);
        # other tables in the PDF have year-led rows too.
        if m and int(m.group(2).replace(",", "")) > 100_000:
            births, deaths, nat = (int(m.group(i).replace(",", ""))
                                   for i in (5, 6, 7))
            # Rounded thousands: the difference may be off by one.
            if abs(births - deaths - nat) > 1:
                raise RuntimeError(f"Stat Bureau {m.group(1)}: "
                                   f"{births}-{deaths} != {nat}")
            out.setdefault(int(m.group(1)), (births, deaths))
    if len(out) < 10:
        raise RuntimeError("Statistics Bureau gaiyou: table 2 not parsed")
    return out


def world_bank(code: str) -> dict[int, float]:
    blob = fetch(WB.format(code=code), f"mhlw_xcheck_wb_{code}.json",
                 (b"[",))
    payload = json.loads(blob)
    if len(payload) < 2 or not payload[1]:
        raise RuntimeError(f"World Bank {code}: empty payload")
    return {int(r["date"]): r["value"] for r in payload[1]
            if r["value"] is not None}


def cross_checks(v: dict[int, dict], life: dict[int, dict]) -> None:
    sb = stat_bureau_vital()
    years = [y for y in sorted(sb) if y >= 2015 and y in v]
    if len(years) < 5:
        raise SystemExit(f"  !! Statistics Bureau overlap only {years}")
    for y in years:
        sb_b, sb_d = sb[y]
        d_gap = sb_d * 1000 / v[y]["deaths"] - 1
        b_gap = sb_b * 1000 / v[y]["births"] - 1
        # The Bureau's year runs October to September and counts every
        # resident. Deaths: within 4% of MHLW's calendar-year Japanese
        # count in any one year (a winter wave lands in different years:
        # 2022 is -2.5%). Births: the Bureau must run ABOVE MHLW (births
        # to foreign parents) but by less than 9%.
        if abs(d_gap) > 0.04:
            raise SystemExit(f"  !! deaths {y}: Stat Bureau {sb_d}k vs MHLW "
                             f"{v[y]['deaths']:,} ({d_gap:+.1%})")
        if not 0 < b_gap < 0.09:
            raise SystemExit(f"  !! births {y}: Stat Bureau {sb_b}k vs MHLW "
                             f"{v[y]['births']:,} ({b_gap:+.1%})")
        print(f"  ok {y} vs Statistics Bureau (Oct–Sep, all residents): "
              f"deaths {d_gap:+.1%}, births {b_gap:+.1%}")
    # Summed over the overlap the period shift washes out: deaths must
    # agree within 1.5%.
    tot = sum(sb[y][1] for y in years) * 1000 / sum(v[y]["deaths"]
                                                    for y in years) - 1
    if abs(tot) > 0.015:
        raise SystemExit(f"  !! deaths {years[0]}–{years[-1]} summed: "
                         f"{tot:+.1%} against the Statistics Bureau")
    print(f"  ok deaths {years[0]}–{years[-1]} summed vs Statistics Bureau: "
          f"{tot:+.2%}")
    # The World Bank republishes MHLW's own TFR and life expectancy (same
    # Japanese-national scope), so these must match to rounding.
    tfr = world_bank("SP.DYN.TFRT.IN")
    for y in (2006, 2015, 2024):
        check(f"{y} TFR vs World Bank", v[y]["tfr"], tfr[y], 0.011)
    for code, key in (("SP.DYN.LE00.MA.IN", "e0_male"),
                      ("SP.DYN.LE00.FE.IN", "e0_female")):
        wb = world_bank(code)
        for y in (2019, 2023):
            check(f"{y} {key} vs World Bank", life[y][key], wb[y], 0.06)
    # Births magnitude: WB crude birth rate × WB mid-year TOTAL population
    # must land within 6% above MHLW's Japanese births (the rate is MHLW's
    # per Japanese population; the WB population includes foreigners).
    cbr, pop = world_bank("SP.DYN.CBRT.IN"), world_bank("SP.POP.TOTL")
    for y in (2006, 2024):
        implied = cbr[y] * pop[y] / 1000
        gap = implied / v[y]["births"] - 1
        if not -0.01 < gap < 0.06:
            raise SystemExit(f"  !! births {y}: WB implied {implied:,.0f} vs "
                             f"MHLW {v[y]['births']:,} ({gap:+.1%})")
        print(f"  ok {y} births vs World Bank CBR×population: {gap:+.1%}")


# ------------------------------------------------------------------- main

def main() -> None:
    print("MHLW")
    eds = editions(VITAL_LIST, "mhlw_vital_list.html",
                   r"jinkou/kakutei(\d\d)/")
    latest = eds[0]
    print(f"  vital statistics: newest final edition {latest}")
    books = {y: edition_workbook(y, CAUSE_TITLE)
             for y in range(Y0, latest + 1)}

    v = vital(latest, books[latest], books[latest - 1])

    causes = {y: causes_of(y, books[y]) for y in books}
    for y, spot in SPOT_CAUSES.items():
        for code, want in spot.items():
            check(f"{y} cause {code}", causes[y].get(code, (None,))[0],
                  want, 0)
    # The newest edition repeats the previous year's totals: they must
    # equal the previous edition's own (no silent revision of causes).
    prev_col = {}
    for _, rows in books[latest]:
        if CAUSE_TITLE in title_text(rows, 3):
            for r in rows:
                if len(r) > 6 and re.fullmatch(r"\d{5}", norm(r[1])):
                    prev_col[norm(r[1])] = count(r[6])
    diffs = [c for c in CAUSES if prev_col.get(c) is not None and
             prev_col[c] != causes[latest - 1].get(c, (None,))[0]]
    if not any(prev_col.get(c) is not None for c in CAUSES):
        raise SystemExit(f"  !! causes: the {latest} edition no longer "
                         f"repeats {latest - 1}; revisit the revision check")
    if diffs:
        raise SystemExit(f"  !! causes {latest - 1} revised in the "
                         f"{latest} edition: {diffs}")
    print(f"  ok causes {latest - 1}: {latest} edition repeats the "
          f"{latest - 1} edition exactly")

    life_ed = editions(LIFE_LIST, "mhlw_life_list.html",
                       r"life/life(\d\d)/")[0]
    life = life_year_series(life_ed)
    for y, (m, f) in SPOT_LIFE.items():
        check(f"{y} e0 male", life[y]["e0_male"], m, 0.001)
        check(f"{y} e0 female", life[y]["e0_female"], f, 0.001)
    census_abridged = {y: abridged_table(y) for y in range(Y0, life_ed + 1)
                       if y in life and life[y]["kind"] == "complete"}
    for y, ab in census_abridged.items():
        # Complete and abridged tables of one year differ by tenths, not
        # by years: a misread column fails here.
        for k, val in ab.items():
            if abs(val - life[y][k]) > 0.5:
                raise SystemExit(f"  !! {y} {k}: abridged {val} vs complete "
                                 f"{life[y][k]}")
        print(f"  ok {y} abridged table read beside the complete one: "
              f"e0 {ab['e0_male']}/{ab['e0_female']} vs "
              f"{life[y]['e0_male']}/{life[y]['e0_female']}")

    pov_ed, pov, pov_url = poverty()
    for y, spot in SPOT_POVERTY.items():
        for k, want in spot.items():
            check(f"poverty {y} {k}", pov[y].get(k), want, 0.001)

    cross_checks(v, life)

    # ---------------------------------------------------------- writing
    vcols = ["births", "deaths", "natural_change", "infant_deaths",
             "marriages", "divorces", "birth_rate", "death_rate",
             "natural_change_rate", "infant_mortality_rate", "tfr"]
    write("demography/vital_from_mhlw.csv", f"""
MHLW Vital Statistics, final figures (人口動態統計 確定数), {latest} edition,
第2表/第3表 人口動態総覧の年次推移 (the long series, revised). Calendar years
of occurrence. SCOPE: JAPANESE NATIONALS IN JAPAN (日本における日本人) —
births to foreign parents and deaths of foreign residents are excluded,
and rates use the Japanese population; the Statistics Bureau's
total-population births (Oct–Sep) run ~2-5% higher. Counts are persons (marriages
and divorces are couples). birth_rate, death_rate, natural_change_rate per
1,000 population; infant_mortality_rate per 1,000 live births; tfr = total
fertility rate (合計特殊出生率). Includes the 2019-03-29 re-tabulation of
2006 and 2009-2017 (prefectural under-reporting), so some figures differ
from the editions first published for those years.""",
          ["year"] + vcols, [[y] + [v[y].get(k) for k in vcols]
                             for y in sorted(v)])

    gaps = {y: causes[y]["total"][0] - v[y]["deaths"] for y in causes
            if y in v and causes[y]["total"][0] != v[y]["deaths"]}
    gap_text = ", ".join(f"{y} {g:+d}" for y, g in sorted(gaps.items()))
    write("mortality/causes_from_mhlw.csv", f"""
MHLW Vital Statistics, final figures: deaths by the abridged cause list
(死因簡単分類), each year read from THAT year's own edition (table found by
its title 死因簡単分類別にみた性別死亡数; its number moves). Persons, calendar
year of death, JAPANESE NATIONALS IN JAPAN only. Column suffix = cause code.
all_causes is the edition's own total; all_causes_revised is the 第2表 long
series after the 2019 re-tabulation. Edition minus revised: {gap_text or 'none'}.
Causes are NOT re-tabulated for those years — the gap is unallocated.
BREAK 2017: ICD-10 (2013 version) adopted; aspiration_pneumonia_10601 split
out of pneumonia_10200 (blank before 2017, never added back).
COVID-19: special_purpose_codes_22200 (U-codes; in 2020-2022 this is COVID-19
in practice) and covid19_22201 (split out from the 2023 edition) — two columns.
senility_18100 (老衰) is a certified underlying cause used far more in Japan
than elsewhere. MHLW '-' = 0; a code absent from an edition is blank.""",
          ["year", "all_causes", "all_causes_revised"] + list(
              CAUSES.values()),
          [[y, causes[y]["total"][0], v.get(y, {}).get("deaths")] +
           [causes[y].get(c, (None,))[0] for c in CAUSES]
           for y in sorted(causes)])

    write("security/homicide_deaths_from_mhlw.csv", """
MHLW Vital Statistics, cause 20300 他殺 (assault; deaths certified as
homicide), persons, calendar year of death, JAPANESE NATIONALS IN JAPAN
only, each year from its own edition (same table as causes_from_mhlw.csv).
A count of DEATHS. The National Police Agency's 殺人 count is of recorded
OFFENCES and includes attempts and preparation (未遂・予備): 976 in 2025
against 211 deaths here. Two publishers, two definitions — never spliced.""",
          ["year", "homicide_deaths", "male", "female"],
          [[y, *causes[y]["20300"]] for y in sorted(causes)])

    lrows = []
    for y in range(Y0, Y1 + 1):
        if y not in life:
            continue
        rec = life[y]
        ab = census_abridged.get(y)
        if rec["kind"] == "abridged":
            ab = {k: rec[k] for k in ("e0_male", "e0_female", "e65_male",
                                      "e65_female")}
        comp = rec if rec["kind"] == "complete" else {}
        lrows.append([y] + [ab.get(k) if ab else None for k in
                            ("e0_male", "e0_female", "e65_male",
                             "e65_female")] +
                     [comp.get(k) for k in ("e0_male", "e0_female",
                                            "e65_male", "e65_female")])
    write("demography/life_expectancy_from_mhlw.csv", f"""
MHLW life tables, years. *_abridged = 簡易生命表 (every year; year series
参考資料2 of the {life_ed} edition, census years read from those years' own
abridged tables). *_complete = 完全生命表 (census years only: 2010, 2015,
2020). One kind per column, never joined. e0 = life expectancy at birth,
e65 = at 65. Japanese nationals in Japan.""",
          ["year", "e0_male_abridged", "e0_female_abridged",
           "e65_male_abridged", "e65_female_abridged", "e0_male_complete",
           "e0_female_complete", "e65_male_complete", "e65_female_complete"],
          lrows)

    pcols = ["poverty_rate_old", "poverty_rate_new", "child_poverty_old",
             "child_poverty_new", "median_income_old", "median_income_new",
             "poverty_line_old", "poverty_line_new"]
    write("social/poverty_from_mhlw.csv", f"""
MHLW Comprehensive Survey of Living Conditions {pov_ed} (国民生活基礎調査),
表11 貧困率の年次推移 ({pov_url.rsplit('/', 1)[-1]}). `year` is the INCOME year;
the survey is taken the following year. Large-scale survey every THREE
years; the years between are holes. Relative poverty rate = share of
people below half the median equivalised disposable income, per cent
(OECD method); child = aged 17 or under. median_income and poverty_line
are in 10,000 yen (万円), nominal. *_old = 旧基準 income definition, *_new =
新基準 (OECD 2015: also deducts car taxes, corporate-pension contributions
and remittances); 2018 is published on both — the seam. 1994 excludes
Hyogo; 2015 excludes Kumamoto.""",
          ["year", "survey_year"] + pcols,
          [[y, y + 1] + [pov[y].get(k) for k in pcols]
           for y in sorted(pov) if y >= Y0])

    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
