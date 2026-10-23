#!/usr/bin/env python3
"""Refresh the National Statistics Office series for Vietnam.

Usage:  python3 -I countries/vietnam/fetch/fetch_nso.py

Cục Thống kê, the National Statistics Office (NSO, the former GSO, now
under the Ministry of Finance), is the national publisher for nearly
every chapter: national accounts, prices, the state budget (republished
from the MOF), trade (from Customs), credit, rates and the BoP (from the
SBV), population, vitals, labour, income, Gini, poverty, justice, road
safety and HIV. Its database is PxWeb 2019 at pxweb.nso.gov.vn, and
gso.gov.vn no longer resolves.

**Two doors, one of which rounds.**

  1. The PxWeb JSON API, /api/v1/vi/<db>/<table>.px, serves only five
     databases (population and labour among them). It rounds every value
     to the table's SHOWDECIMALS, so the total fertility rate comes back
     as "2" for every year.
  2. The HTML table pages, /pxweb/vi/<db>/<db>/<table>.px/, serve every
     database at full precision. They are ASP.NET WebForms: GET the page,
     post back every hidden field, every <option> of each ValuesListBox,
     OutputFormatDropDownList=FileTypeJsonStat and ButtonViewTable. The
     reply is a JSON-stat v1 attachment, UTF-8 with a BOM and ONE TRAILING
     NUL BYTE.

Every number written here comes through door 2. Door 1 is used only as
an independent cross-check where its rounding is harmless (population
in thousands to 2 dp, the unemployment rate to 2 dp): the fetcher asserts
the two doors agree to the API's rounding.

**Errors arrive as HTTP 200.** A bad path or an expired form lands on
/ErrorGeneral.aspx with status 200, so the status code proves nothing.
The fetcher asserts the content-disposition header names an attachment,
that the payload has a `dataset` key, and that the value count equals
the product of the dimension sizes, before anything is cached.

**Labels.** Year labels carry status: "Sơ bộ 2025" is preliminary and
"Ước tính 2025" an estimate; the year is parsed off and the status kept
in a column (where files merge tables, the most tentative status wins).
Labels are NFC-normalised, and a handful of tables (V14.46, V14.87) spell
Đ with U+00D0, the Icelandic eth, which NFC does not fix; it is mapped to
U+0110. Every series is picked by position AND a substring of its label,
so a reordered or relabelled table fails rather than shifting columns.
Units are scraped from each table page ("Đơn vị tính") into the comments.

**Breaks, kept apart and never spliced.**

  * GDP revaluation: V03.01 carries 2000–2002 and 2009 on the OLD scale
    and 2010+ on the revalued one (2003–2008 are absent). Every level
    column is written twice, `_old_scale` (≤2009) and `_revalued`
    (≥2010). The PX NOTEX that records the revaluation is fetched and
    asserted to still be there.
  * Gini 2019→2020 (0.423 → 0.375), undocumented: every Gini column is
    split into `_2002_2019` and `_2020_on`.
  * Traffic deaths 2021→2022 (5,790 → 13,551), a reclassification:
    accidents, deaths and injuries are split into `_to2021` and
    `_from2022`, and the step is asserted so a back-revision is noticed.
  * Poverty: V14.46 (poverty_from_gso) and V14.01 (hdi_from_gso) are two
    tables that disagree on 2016 (5.8 vs 9.2); they go to two files. The
    standard change within V14.46 is a `standard` column, derived from
    the PX NOTEX (asserted present) and the V14.01 comparison.
  * Life expectancy 2021 = 2022 = 73.64 is asserted and flagged as a
    probable carried value.

**The budget year is the calendar year.** Vietnam's state-budget year
runs 1 January to 31 December (Law on the State Budget), so the fiscal
files are keyed on calendar year; no April keying applies here.

Outputs are `_from_gso` sidecars under data/ (the manifest's names keep
the old acronym). Nothing here overwrites a curated file.
"""
from __future__ import annotations

import csv
import http.cookiejar
import json
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache"

HOST = "https://pxweb.nso.gov.vn"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) worldreports-fetch",
      "Accept-Language": "vi,en;q=0.5"}
GAP = 2.0                     # seconds between NSO requests
YEAR = "Năm"                  # the time dimension of every NSO table

NA = "Tài khoản quốc gia"
PRICES = "Chỉ số giá"
TRADE = "Xuất nhập khẩu"
SOCIAL = "Y tế, văn hóa và MSDC"
POP = "Dân số và lao động"

REGIONS = [("Đồng bằng sông Hồng", "red_river_delta"),
           ("Trung du và miền núi phía Bắc", "northern_midlands_mountains"),
           ("Bắc Trung Bộ và", "north_central_coast"),
           ("Tây Nguyên", "central_highlands"),
           ("Đông Nam Bộ", "southeast"),
           ("Đồng bằng sông Cửu Long", "mekong_delta")]

# ---------------------------------------------------------------- transport

_jar = http.cookiejar.CookieJar()
_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_jar))
_last = [0.0]


def _request(url: str, data: bytes | None = None, headers=None):
    """One request, spaced and retried. Returns (final url, headers, body)."""
    last = None
    for attempt in range(4):
        wait = _last[0] + GAP - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        try:
            req = urllib.request.Request(url, data=data,
                                         headers={**UA, **(headers or {})})
            with _opener.open(req, timeout=180) as r:
                out = (r.geturl(), r.headers, r.read())
            _last[0] = time.monotonic()
            return out
        except urllib.error.HTTPError as e:
            _last[0] = time.monotonic()
            last = e
            if e.code == 404:
                raise RuntimeError(f"{url}: HTTP 404") from e
            if e.code in (403, 429, 500, 502, 503, 504):
                time.sleep(30 * (attempt + 1))
                continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            _last[0] = time.monotonic()
            last = e
            time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"{url}: {last}")


class _Form(HTMLParser):
    """The PxWeb selection form's fields, as a browser would post them."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.fields: list[tuple[str, str]] = []
        self.selects: dict[str, list[tuple[str, bool]]] = {}
        self.button: tuple[str, str] | None = None
        self._sel: str | None = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        name = a.get("name")
        if tag == "input" and name:
            kind = (a.get("type") or "text").lower()
            if kind in ("hidden", "text"):
                self.fields.append((name, a.get("value") or ""))
            elif kind == "submit" and name.endswith("$ButtonViewTable"):
                self.button = (name, a.get("value") or "")
        elif tag == "select" and name:
            self._sel = name
            self.selects[name] = []
        elif tag == "option" and self._sel is not None:
            self.selects[self._sel].append((a.get("value", ""),
                                            "selected" in a))

    def handle_endtag(self, tag):
        if tag == "select":
            self._sel = None


def _q(s: str) -> str:
    return urllib.parse.quote(s, safe="")


def page_url(db: str, table: str) -> str:
    return f"{HOST}/pxweb/vi/{_q(db)}/{_q(db)}/{_q(table)}.px/"


def _export(db: str, table: str, fmt: str) -> tuple[bytes, str]:
    """Drive the form for the whole table; returns (attachment, unit)."""
    url = page_url(db, table)
    final, _, page = _request(url)
    if "ErrorGeneral" in final:
        raise RuntimeError(f"{table}: table page redirected to {final}")
    html = page.decode("utf-8")
    form = _Form()
    form.feed(html)
    boxes = [n for n in form.selects if n.endswith("$ValuesListBox")]
    if not boxes or form.button is None:
        raise RuntimeError(f"{table}: no selection form on {final}")
    fields = list(form.fields)
    for name, opts in form.selects.items():
        if name in boxes:
            if not opts:
                raise RuntimeError(f"{table}: empty ValuesListBox {name}")
            fields += [(name, v) for v, _ in opts]
        elif name.endswith("$OutputFormatDropDownList"):
            if fmt not in {v for v, _ in opts}:
                raise RuntimeError(f"{table}: output format {fmt} not offered")
            fields.append((name, fmt))
        elif opts:
            chosen = [v for v, s in opts if s] or [opts[0][0]]
            fields += [(name, v) for v in chosen]
    fields.append(form.button)
    m = re.search(r'information_unit_value">\s*(.*?)\s*<', html, re.S)
    unit = clean(m.group(1)) if m else ""
    final2, hdr, blob = _request(
        final, urllib.parse.urlencode(fields).encode(),
        {"Content-Type": "application/x-www-form-urlencoded",
         "Referer": final})
    disp = hdr.get("Content-Disposition") or ""
    if "attachment" not in disp.lower() or "ErrorGeneral" in final2:
        raise RuntimeError(f"{table}: no attachment (landed on {final2}, "
                           f"content-disposition {disp!r})")
    return blob, unit


def jsonstat(db: str, table: str) -> dict:
    """The whole table through the HTML door, JSON-stat v1, cached."""
    CACHE.mkdir(exist_ok=True)
    local = CACHE / f"nso_{table}.json"
    if local.exists():
        return json.loads(local.read_text(encoding="utf-8"))
    blob, unit = _export(db, table, "FileTypeJsonStat")
    if blob.startswith(b"\xef\xbb\xbf"):
        blob = blob[3:]
    blob = blob.rstrip(b"\x00\r\n ")
    data = json.loads(blob.decode("utf-8"))
    ds = data.get("dataset")
    if not isinstance(ds, dict) or "value" not in ds or "dimension" not in ds:
        raise RuntimeError(f"{table}: payload has no dataset key")
    n = 1
    for s in ds["dimension"]["size"]:
        n *= s
    if len(ds["value"]) != n:
        raise RuntimeError(f"{table}: {len(ds['value'])} values, {n} cells")
    if YEAR not in ds["dimension"]["id"]:
        raise RuntimeError(f"{table}: no {YEAR!r} dimension")
    if all(v is None for v in ds["value"]):
        raise RuntimeError(f"{table}: every cell is empty")
    data["_fetch"] = {"url": page_url(db, table), "unit": unit,
                      "fetched": time.strftime("%Y-%m-%d")}
    local.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def px_notex(db: str, table: str) -> str:
    """The table's PX NOTEX field. The PX export is iso-8859-15, so its
    Vietnamese letters arrive as '?'; only ASCII fragments are asserted."""
    CACHE.mkdir(exist_ok=True)
    local = CACHE / f"nso_{table}.px"
    if not local.exists():
        blob, _ = _export(db, table, "FileTypePX")
        if b"MATRIX=" not in blob[:4000] or b"DATA=" not in blob:
            raise RuntimeError(f"{table}: PX export is not a PX file")
        local.write_bytes(blob)
    text = local.read_bytes().decode("iso-8859-15")
    m = re.search(r'NOTEX(?:\[[^\]]*\])?="(.*?)";', text, re.S)
    return m.group(1).replace('"\r\n"', "").replace('"\n"', "") if m else ""


def api_table(db: str, table: str) -> dict[tuple[str, ...], str]:
    """Door 1: the JSON API, every cell, keyed by value TEXTS. Rounded."""
    CACHE.mkdir(exist_ok=True)
    local = CACHE / f"nso_api_{table}.json"
    url = f"{HOST}/api/v1/vi/{_q(db)}/{_q(table)}.px"
    if not local.exists():
        _, _, blob = _request(url)
        meta = json.loads(blob.decode("utf-8-sig"))
        if "variables" not in meta:
            raise RuntimeError(f"API {table}: no variables in metadata")
        query = {"query": [{"code": v["code"],
                            "selection": {"filter": "item",
                                          "values": v["values"]}}
                           for v in meta["variables"]],
                 "response": {"format": "json"}}
        _, _, blob = _request(url, json.dumps(query).encode(),
                              {"Content-Type": "application/json"})
        reply = json.loads(blob.decode("utf-8-sig").rstrip("\x00"))
        if not reply.get("data"):
            raise RuntimeError(f"API {table}: empty data")
        local.write_text(json.dumps({"meta": meta, "reply": reply},
                                    ensure_ascii=False), encoding="utf-8")
    both = json.loads(local.read_text(encoding="utf-8"))
    texts = [dict(zip(v["values"], v["valueTexts"]))
             for v in both["meta"]["variables"]]
    return {tuple(clean(texts[i][k]) for i, k in enumerate(row["key"])):
            row["values"][0] for row in both["reply"]["data"]}


# ---------------------------------------------------------------- parsing

def clean(s: str) -> str:
    s = unicodedata.normalize("NFC", s).replace("Ð", "Đ")
    return re.sub(r"\s+", " ", s).strip()


STATUS_RANK = {"final": 0, "preliminary": 1, "estimate": 2}


def parse_year(label: str) -> tuple[int, str, str]:
    m = re.search(r"(\d{4})", label)
    if not m:
        raise RuntimeError(f"unparseable year label {label!r}")
    status = ("preliminary" if "Sơ bộ" in label else
              "estimate" if "Ước tính" in label else "final")
    marker = re.sub(r"[^*]", "", label)
    return int(m.group(1)), status, marker


class Table:
    def __init__(self, db: str, code: str):
        self.code = code
        data = jsonstat(db, code)
        ds = data["dataset"]
        self.title = clean(ds.get("label") or "")
        self.updated = ds.get("updated") or ""
        self.unit = data["_fetch"]["unit"]
        self.url = data["_fetch"]["url"]
        self.ids = ds["dimension"]["id"]
        self.size = ds["dimension"]["size"]
        self.labels: dict[str, list[str]] = {}
        for d in self.ids:
            cat = ds["dimension"][d]["category"]
            order = sorted(cat["index"], key=lambda k: cat["index"][k])
            self.labels[d] = [clean(cat["label"][k]) for k in order]
        self.values = ds["value"]
        self.years = {}
        for lab in self.labels[YEAR]:
            y, st, mk = parse_year(lab)
            if y in self.years:
                raise RuntimeError(f"{code}: year {y} twice")
            self.years[y] = (lab, st, mk)

    def dim(self, name: str) -> list[str]:
        if name not in self.labels:
            raise RuntimeError(f"{self.code}: no dimension {name!r} "
                               f"(has {self.ids})")
        return self.labels[name]

    def match(self, name: str, spec: list[tuple[str, str]]) -> list[tuple[str, str]]:
        """Pair each label of a dimension with a column name, asserting
        the count and that each label contains the expected fragment."""
        labs = self.dim(name)
        if len(labs) != len(spec):
            raise RuntimeError(f"{self.code}/{name}: {len(labs)} values, "
                               f"expected {len(spec)}: {labs}")
        for lab, (frag, _) in zip(labs, spec):
            if frag not in lab:
                raise RuntimeError(f"{self.code}/{name}: {lab!r} does not "
                                   f"contain {frag!r}")
        return [(lab, col) for lab, (_, col) in zip(labs, spec)]

    def series(self, **fixed: str) -> dict[int, float | None]:
        """One series over the years; `fixed` names a label for every other
        dimension, keyed by the dimension's name as published."""
        out = {}
        for y, (lab, _, _) in self.years.items():
            coord = {**fixed, YEAR: lab}
            idx = 0
            for d, n in zip(self.ids, self.size):
                if d not in coord:
                    raise RuntimeError(f"{self.code}: no label for {d!r}")
                try:
                    pos = self.labels[d].index(coord[d])
                except ValueError:
                    raise RuntimeError(f"{self.code}/{d}: no {coord[d]!r}")
                idx = idx * n + pos
            out[y] = self.values[idx]
        return out


class Frame:
    """A wide sidecar: one row per year, a status column, named columns."""

    def __init__(self):
        self.cols: dict[str, dict[int, float | None]] = {}
        self.desc: dict[str, str] = {}
        self.status: dict[int, str] = {}
        self.tables: list[Table] = []
        self.extra: dict[str, dict[int, str]] = {}

    def use(self, t: Table) -> None:
        self.tables.append(t)
        for y, (_, st, _) in t.years.items():
            old = self.status.get(y, "final")
            self.status[y] = max(old, st, key=STATUS_RANK.get)

    def add(self, col: str, ser: dict, t: Table, label: str) -> None:
        if col in self.cols:
            raise RuntimeError(f"column {col} twice")
        self.cols[col] = ser
        self.desc[col] = f"{t.code}: {label}"

    def split(self, col: str, ser: dict, t: Table, label: str, cut: int,
              before: str, after: str) -> None:
        self.add(f"{col}_{before}",
                 {y: v for y, v in ser.items() if y < cut}, t, label)
        self.add(f"{col}_{after}",
                 {y: v for y, v in ser.items() if y >= cut}, t, label)

    def get(self, col: str, year: int):
        return self.cols[col].get(year)

    def write(self, rel: str, comment: str, extra_first: list[str] = ()):
        years = sorted(self.status)
        header = ["year", "status", *extra_first, *self.cols]
        rows = [[y, self.status[y], *[self.extra[c].get(y, "")
                                      for c in extra_first],
                 *[fmt(self.cols[c].get(y)) for c in self.cols]]
                for y in years]
        lines = [comment.strip(), ""]
        for t in self.tables:
            lines.append(f"{t.code} \"{t.title}\" — unit on the table page: "
                         f"{t.unit or 'not stated'}; NSO updated "
                         f"{t.updated[:10]}; {t.url}")
        lines.append("status: final / preliminary (Sơ bộ) / estimate "
                     "(Ước tính), parsed off the year label.")
        lines.append("Blank = not published for that year. Official: true "
                     "(national statistics office).")
        lines.append("Columns (table: label as published, NFC):")
        lines += [f"  {c} = {self.desc[c]}" for c in self.cols]
        write_csv(rel, "\n".join(lines), header, rows)


def fmt(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        if v.is_integer():
            return str(int(v))
        return "%.10g" % v
    return str(v)


def write_csv(rel: str, comment: str, header: list[str], rows: list[list]):
    """Write a sidecar the shared data tests accept.

    Rows are stable-sorted by year, so a long file keeps its category order
    inside each year. A column the NSO table carries but leaves blank in
    every year is dropped and named in the header, because an empty column
    promises data that does not exist.
    """
    if header and header[0] == "year":
        rows = sorted(rows, key=lambda r: int(r[0]))
    empty = [i for i in range(1, len(header))
             if not any(str(r[i]).strip() for r in rows)]
    if empty:
        comment += ("\nDropped, blank in every year of the published table: "
                    + ", ".join(header[i] for i in empty) + ".")
        keep = [i for i in range(len(header)) if i not in empty]
        header = [header[i] for i in keep]
        rows = [[r[i] for i in keep] for r in rows]
    path = DATA / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        for line in comment.splitlines():
            fh.write(f"# {line}".rstrip() + "\n")
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    span = f"{rows[0][0]}–{rows[-1][0]}" if rows else "EMPTY"
    print(f"  data/{rel}  {len(rows)} rows ({span}), {len(header)} columns")


def expect(what: str, got, want: float, tol: float | None = None) -> None:
    """Raise unless `got` equals `want` to the precision `want` is written in."""
    if tol is None:
        s = repr(float(want))
        dec = len(s.split(".")[1]) if "." in s and not s.endswith(".0") else 0
        tol = 0.5 * 10 ** -dec + 1e-9
    if got is None or abs(got - want) > tol:
        raise RuntimeError(f"{what}: got {got}, expected {want} (±{tol})")


def absent(what: str, ser: dict, years) -> None:
    for y in years:
        if ser.get(y) is not None:
            raise RuntimeError(f"{what}: {y} expected absent, got {ser[y]}")


def grid(f: Frame, t: Table, rows: list[tuple[str, str]], dim: str,
         fixed: dict[str, str] | None = None, suffix: str = "") -> None:
    for lab, col in rows:
        f.add(col + suffix, t.series(**{dim: lab, **(fixed or {})}), t, lab)


# ---------------------------------------------------------------- macro

GDP_ROWS = [
    ("Tổng sản phẩm trong nước theo giá hiện hành - Tỷ đồng", "gdp_cur_vnd_bn"),
    ("Nội tệ - Triệu đồng", "gdp_pc_cur_vnd_mn"),
    ("Ngoại tệ (theo tỷ giá TTBQ liên NH) - USD", "gdp_pc_cur_usd"),
    ("Tích luỹ tài sản theo giá hiện hành", "capital_formation_cur_vnd_bn"),
    ("Tiêu dùng cuối cùng theo giá hiện hành", "final_consumption_cur_vnd_bn"),
    ("Xuất khẩu hàng hoá và dịch vụ theo giá", "exports_gs_cur_vnd_bn"),
    ("Nhập khẩu hàng hoá và dịch vụ theo giá", "imports_gs_cur_vnd_bn"),
    ("Tổng thu nhập quốc gia theo giá hiện hành", "gni_cur_vnd_bn"),
    ("theo giá so sánh 2010 - Tỷ đồng", "gdp_const2010_vnd_bn"),
    ("Tốc độ tăng tổng sản phẩm", "real_growth_pct"),
    ("Tích luỹ tài sản so với GDP", "capital_formation_pct_gdp"),
    ("Tài sản cố định so với GDP", "fixed_assets_pct_gdp"),
    ("Tiêu dùng cuối cùng so với GDP", "final_consumption_pct_gdp"),
    ("Xuất khẩu hàng hoá và dịch vụ so với GDP", "exports_gs_pct_gdp"),
    ("Nhập khẩu hàng hoá và dịch vụ so với GDP", "imports_gs_pct_gdp"),
    ("Tổng thu nhập quốc gia so với GDP", "gni_pct_gdp"),
]
GDP_LEVELS = 9          # the first nine rows are levels on the GDP scale


def gdp() -> dict:
    t = Table(NA, "V03.01")
    note = px_notex(NA, "V03.01")
    if "2010" not in note or "GDP" not in note:
        raise RuntimeError(f"V03.01: revaluation NOTEX gone: {note!r}")
    f = Frame()
    f.use(t)
    for i, (lab, col) in enumerate(t.match("Chỉ tiêu", GDP_ROWS)):
        ser = t.series(**{"Chỉ tiêu": lab})
        if i < GDP_LEVELS:
            f.split(col, ser, t, lab, 2010, "old_scale", "revalued")
        else:
            f.add(col, ser, t, lab)
    f.extra["gdp_scale"] = {y: "old" if y < 2010 else "revalued"
                            for y in t.years}
    g = f.cols
    expect("GDP 2024", g["gdp_cur_vnd_bn_revalued"][2024], 11510329)
    expect("GDP 2025", g["gdp_cur_vnd_bn_revalued"][2025], 12847571)
    expect("GDP 2009 old scale", g["gdp_cur_vnd_bn_old_scale"][2009], 1809149)
    expect("GDP 2010 revalued", g["gdp_cur_vnd_bn_revalued"][2010], 2739843)
    expect("GDP/person 2024 USD", g["gdp_pc_cur_usd_revalued"][2024], 4700)
    expect("GDP/person 2025 USD", g["gdp_pc_cur_usd_revalued"][2025], 5026)
    for y, v in {2020: 2.87, 2021: 2.55, 2022: 8.54, 2025: 8.02}.items():
        expect(f"real growth {y}", g["real_growth_pct"][y], v)
    absent("V03.01 2003-2008", {y: 1 for y in t.years}, range(2003, 2009))
    f.write("macro/gdp_from_gso.csv", """
NSO national accounts, V03.01 (Một số chỉ tiêu chủ yếu về tài khoản quốc gia).
Current-price levels in bn VND (tỷ đồng); GDP per person in mn VND (triệu
đồng) and in US$ (converted at the average interbank rate); constant prices
are 2010 prices; ratios in % of current-price GDP; real growth in % y/y.
THE GDP REVALUATION SEAM: the NSO revalued GDP upward from 2010 only (PX
NOTEX: "Số liệu từ năm 2010 là số liệu theo quy mô GDP đánh giá lại").
2000-2002 and 2009 are on the OLD scale, 2010+ on the REVALUED scale, and
2003-2008 are absent from the table. Each level is therefore two columns,
_old_scale (<=2009) and _revalued (>=2010), never joined: a 2009->2010
change in level is methodology, not growth. The ratio and growth columns
are single columns; gdp_scale says which scale their denominator is on.
""", extra_first=["gdp_scale"])
    return {"gdp_bn": g["gdp_cur_vnd_bn_revalued"],
            "gdp_pc_usd": g["gdp_pc_cur_usd_revalued"]}


CPI_ROWS = [
    ("Chỉ số giá tiêu dùng", "cpi"), ("Hàng ăn và dịch vụ ăn uống", "food_catering"),
    ("Lương thực", "staple_food"), ("Thực phẩm", "foodstuffs"),
    ("Ăn uống ngoài gia đình", "eating_out"),
    ("Đồ uống và thuốc lá", "beverages_tobacco"),
    ("May mặc", "clothing_footwear"), ("Nhà ở, điện nước", "housing_utilities"),
    ("Thiết bị và đồ dùng gia đình", "household_goods"),
    ("Thuốc và dịch vụ y tế", "medicine_health"),
    ("Dịch vụ y tế", "of_which_health_services"), ("Giao thông", "transport"),
    ("Thông tin và truyền thông", "communications"), ("Giáo dục", "education"),
    ("Dịch vụ giáo dục", "of_which_education_services"),
    ("Văn hóa, giải trí và du lịch", "culture_recreation"),
    ("Hàng hoá và dịch vụ khác", "other_goods_services"),
    ("Chỉ số giá vàng", "gold_price_index"), ("Chỉ số đô la Mỹ", "usd_price_index"),
    ("Lạm phát cơ bản", "core_inflation_index"),
]


def cpi() -> None:
    t = Table(PRICES, "V11.08")
    f = Frame()
    f.use(t)
    grid(f, t, t.match("Nhóm hàng", CPI_ROWS), "Nhóm hàng")
    for y, v in {2008: 122.97, 2011: 118.58, 2023: 103.25, 2024: 103.63,
                 2025: 103.31}.items():
        expect(f"CPI {y}", f.get("cpi", y), v)
    absent("core inflation before 2010", f.cols["core_inflation_index"],
           [y for y in t.years if y < 2010])
    f.write("macro/cpi_from_gso.csv", """
NSO V11.08: annual-average price indices, PREVIOUS YEAR = 100 (inflation =
value - 100). CPI and its groups, the gold price index, the US-dollar price
index and core inflation (lạm phát cơ bản, published from 2010; earlier
cells are blank because they were never compiled). Years 2000, 2003-2025.
The gold and USD indices are price indices, not exchange or policy rates.
""")


# ---------------------------------------------------------------- fiscal

REV_ROWS = [
    ("TỔNG THU", "total"), ("Thu trong nước", "domestic_ex_crude"),
    ("doanh nghiệp Nhà nước", "soe"), ("vốn đầu tư nước ngoài", "fdi_firms"),
    ("ngoài quốc doanh", "nonstate_sector"), ("Thuế thu nhập cá nhân", "pit"),
    ("xổ số", "lottery"), ("phí xăng dầu", "fuel_fee"),
    ("Thuế bảo vệ môi trường", "env_protection_tax"),
    ("Thu phí, lệ phí", "fees_charges"),
    ("Lệ phí trước bạ", "of_which_registration_fee"),
    ("nhà đất", "land_housing"), ("đất nông nghiệp", "agri_land_use_tax"),
    ("Các khoản thu khác", "other"), ("dầu thô", "crude_oil"),
    ("Thu cân đối ngân sách từ hoạt động xuất nhập khẩu", "trade_net"),
    ("Thuế xuất, nhập khẩu", "trade_duties_excise"),
    ("Thuế giá trị gia tăng hàng nhập khẩu", "import_vat"),
    ("Tổng số thu từ hoạt động xuất, nhập khẩu", "trade_gross"),
    ("Hoàn thuế giá trị gia tăng", "vat_refunds"), ("Thu viện trợ", "aid"),
]

EXP_ROWS = [
    ("TỔNG CHI", "total"), ("Chi đầu tư phát triển", "development_investment"),
    ("Chi phát triển sự nghiệp kinh tế - xã hội", "recurrent_socioeconomic"),
    ("giáo dục, đào tạo", "education_training"),
    ("y tế, dân số", "health_population"),
    ("khoa học, công nghệ", "science_technology"),
    ("Chi văn hoá thông tin", "culture_media_sport"),
    ("Chi đảm bảo xã hội", "social_security"),
    ("Chi sự nghiệp kinh tế, bảo vệ môi trường", "economic_environment"),
    ("Quản lý nhà nước, Đảng, đoàn thể", "administration_party"),
    ("quĩ dự trữ tài chính", "financial_reserve_fund"),
]


def _budget(code: str, pct_code: str, dim: str, rows, prefix: str) -> Frame:
    t, tp = Table(NA, code), Table(NA, pct_code)
    f = Frame()
    f.use(t)
    f.use(tp)
    m, mp = t.match(dim, rows), tp.match(dim, rows)
    val, share = t.match("Chỉ tiêu", [("Giá trị (Tỷ đồng)", "vnd_bn"),
                                      ("Cơ cấu (%)", "share_pct")])
    (pct, _), = tp.match("Chỉ tiêu", [("Tỷ lệ (%)", "pct_gdp")])
    for (lab, col), (labp, _) in zip(m, mp):
        f.add(f"{prefix}_{col}_vnd_bn",
              t.series(**{dim: lab, "Chỉ tiêu": val[0]}), t, lab)
        f.add(f"{prefix}_{col}_share_pct",
              t.series(**{dim: lab, "Chỉ tiêu": share[0]}), t, lab)
        f.add(f"{prefix}_{col}_pct_gdp",
              tp.series(**{dim: labp, "Chỉ tiêu": pct}), tp, labp)
    return f


BUDGET_NOTE = """
Keyed on CALENDAR year, which IS Vietnam's budget year (1 January - 31
December under the Law on the State Budget); there is no April fiscal year
here. STATE BUDGET (ngân sách nhà nước: central plus local), cash basis,
source of record the Ministry of Finance. Not general government (ADB GFS)
and never spliced with it. Values in bn VND (tỷ đồng); _share_pct is the
head's share of the total; _pct_gdp is the NSO's own ratio to current GDP
(revalued scale), published for 2018-2025 only. "Ước tính 2025" is an
ESTIMATE, not the final accounts (quyết toán).
"""


def budget(gdp_bn: dict) -> None:
    f = _budget("V03.13-14", "V03.15", "Loại thu", REV_ROWS, "rev")
    for y, v in {2006: 279472, 2020: 1510579, 2024: 2057544,
                 2025: 2681469}.items():
        expect(f"revenue {y}", f.get("rev_total_vnd_bn", y), v)
    expect("revenue 2024 %GDP", f.get("rev_total_pct_gdp", 2024), 17.9, 0.05)
    expect("revenue 2025 %GDP", f.get("rev_total_pct_gdp", 2025), 20.9, 0.05)
    # Second source inside the NSO: revenue over V03.01 GDP.
    expect("revenue/GDP 2024 recomputed",
           100 * f.get("rev_total_vnd_bn", 2024) / gdp_bn[2024], 17.9, 0.1)
    f.write("fiscal/budget_revenue_from_gso.csv",
            "NSO V03.13-14 (Thu ngân sách Nhà nước) and V03.15 (as % of GDP)."
            + BUDGET_NOTE)

    f = _budget("V03.16", "V03.17", "Loại chi", EXP_ROWS, "exp")
    for y, v in {2020: 1709524, 2024: 2148477, 2025: 3312560}.items():
        expect(f"spending {y}", f.get("exp_total_vnd_bn", y), v)
    expect("spending 2024 %GDP", f.get("exp_total_pct_gdp", 2024), 18.7, 0.05)
    expect("spending 2025 %GDP", f.get("exp_total_pct_gdp", 2025), 25.8, 0.05)
    absent("spending 2006", f.cols["exp_total_vnd_bn"], [2006])
    f.write("spending/budget_spending_from_gso.csv",
            "NSO V03.16 (Chi ngân sách Nhà nước) and V03.17 (as % of GDP)."
            + BUDGET_NOTE + """
Budget heads, not COFOG. 2006 is absent from V03.16 and stays blank. The
2025 total (25.8% of GDP against 18.7% in 2024) is an estimate that the
table does not explain.
""")


# ---------------------------------------------------------------- trade

PARTNER_ISO3 = {
    "Bru-nây": "BRN", "Cam-pu-chia": "KHM", "In-đô-nê-xi-a": "IDN",
    "Lào": "LAO", "Ma-lai-xi-a": "MYS", "My-an-ma": "MMR",
    "Phi-li-pin": "PHL", "Xin-ga-po": "SGP", "Thái Lan": "THA",
    "Đài Loan": "TWN", "Hàn Quốc": "KOR", "ĐKHC Hồng Công (TQ)": "HKG",
    "Nhật Bản": "JPN", "CHND Trung Hoa": "CHN", "Ấn Độ": "IND",
    "Băng-la-đét": "BGD", "Pa-ki-xtan": "PAK", "Xri-lan-ka": "LKA",
    "A-rập Xê-út": "SAU", "Các Tiểu vương quốc A-rập Thống nhất": "ARE",
    "Các Tiểu vương quốc Ả-rập Thống nhất": "ARE", "Cô-Oét": "KWT",
    "I-xra-en": "ISR", "Qua-ta": "QAT", "Síp": "CYP", "Thổ Nhĩ Kỳ": "TUR",
    "Ba Lan": "POL", "Bê-la-rút": "BLR", "Bun-ga-ri": "BGR",
    "Hung-ga-ri": "HUN", "LB Nga": "RUS", "Liên Bang Nga": "RUS",
    "Ru-ma-ni": "ROU", "CH Séc": "CZE", "Cộng hòa Séc": "CZE",
    "Xlô-va-ki-a": "SVK", "Slô-va-ki-a": "SVK", "U-crai-na": "UKR",
    "Đan Mạch": "DNK", "Ai-len": "IRL", "Vương quốc Anh": "GBR",
    "Na Uy": "NOR", "Phần lan": "FIN", "Phần Lan": "FIN",
    "Thụy Điển": "SWE", "Bồ Đào Nha": "PRT", "Hy Lạp": "GRC",
    "I-ta-li-a": "ITA", "Tây Ban Nha": "ESP", "Áo": "AUT",
    "CHLB Đức": "DEU", "Bỉ": "BEL", "Hà Lan": "NLD", "Pháp": "FRA",
    "Thụy Sĩ": "CHE", "Ca-na-đa": "CAN", "Hoa Kỳ": "USA",
    "Ác-hen-ti-na": "ARG", "Bra-xin": "BRA", "Chi-lê": "CHL",
    "Mê-hi-cô": "MEX", "Pa-na-ma": "PAN", "Pêru": "PER", "Pê-ru": "PER",
    "Ai Cập": "EGY", "An-giê-ri": "DZA", "Ăng-gô-la": "AGO", "Ga-na": "GHA",
    "Nam Phi": "ZAF", "Ni-giê-ria": "NGA", "Tan-da-nia": "TZA",
    "Xê-nê-gan": "SEN", "Niu- Di-Lân": "NZL", "Niu Di-Lân": "NZL",
    "Ô-xtrây-li-a": "AUS", "Tuy-ni-di": "TUN",
    "Cốt-đi-voa (Bờ biển Ngà)": "CIV",
}
BLOCS = {"ASEAN", "APEC", "EU", "OPEC"}


def trade() -> dict:
    t = Table(TRADE, "V09.01")
    f = Frame()
    f.use(t)
    (val, _), (idx, _) = t.match("Giá trị và chỉ số phát triển", [
        ("Giá trị (Triệu đô la Mỹ)", ""), ("Chỉ số phát triển", "")])
    flows = t.match("Xuất, nhập khẩu", [("Tổng số", "total"),
                                         ("Xuất khẩu", "exports"),
                                         ("Nhập khẩu", "imports"),
                                         ("Cân đối", "balance")])
    for lab, col in flows:
        f.add(f"{col}_usd_mn", t.series(**{"Giá trị và chỉ số phát triển": val,
                                           "Xuất, nhập khẩu": lab}), t, lab)
    for lab, col in flows:
        f.add(f"{col}_index_prev100",
              t.series(**{"Giá trị và chỉ số phát triển": idx,
                          "Xuất, nhập khẩu": lab}), t, f"{lab} ({idx})")
    for y, v in {2006: 39826, 2023: 354721, 2024: 405935, 2025: 474998}.items():
        expect(f"exports {y}", f.get("exports_usd_mn", y), v, 0.5)
    expect("balance 2025", f.get("balance_usd_mn", 2025), 20071, 0.5)
    f.write("trade/trade_totals_from_gso.csv", """
NSO V09.01: merchandise trade, CUSTOMS basis (source of record Vietnam
Customs), US$ millions; _index_prev100 is the growth index, previous year =
100 (balance index as published). Goods only. The BoP basis (V03.20, FOB)
is a different series in international/bop_from_gso.csv.
""")
    totals = {"exports": f.cols["exports_usd_mn"],
              "imports": f.cols["imports_usd_mn"]}

    for code, flow, dim, rel in [
            ("V09.06", "exports", "Khối nước, nước và vùng lãnh thổ",
             "trade/exports_by_partner_from_gso.csv"),
            ("V09.12", "imports", "Khối nước, nước và vùng lãnh thổ chủ yếu",
             "trade/imports_by_partner_from_gso.csv")]:
        tp = Table(TRADE, code)
        labs = tp.dim(dim)
        if labs[0] != "TỔNG SỐ" or labs[1:5] != ["ASEAN", "APEC", "EU", "OPEC"]:
            raise RuntimeError(f"{code}: unexpected head rows {labs[:5]}")
        unknown = [p for p in labs[5:] if p not in PARTNER_ISO3]
        if unknown:
            raise RuntimeError(f"{code}: partners with no ISO3: {unknown}")
        rows, by = [], {}
        for p in labs:
            ser = tp.series(**{dim: p})
            by[p] = ser
            kind = ("total" if p == "TỔNG SỐ" else
                    "bloc" if p in BLOCS else "country")
            for y in sorted(ser):
                rows.append([y, tp.years[y][1], p, PARTNER_ISO3.get(p, ""),
                             kind, fmt(ser[y])])
        # The partner table's total must be the customs total, every year.
        for y, v in by["TỔNG SỐ"].items():
            if v is not None and totals[flow].get(y) is not None:
                expect(f"{code} total {y} vs V09.01", v, totals[flow][y], 1.0)
        if flow == "exports":
            expect("exports to US 2006", by["Hoa Kỳ"][2006], 7845, 0.5)
            expect("exports to US 2024", by["Hoa Kỳ"][2024], 119478, 0.5)
            expect("exports to US 2025", by["Hoa Kỳ"][2025], 153135, 0.5)
            expect("exports to China 2024", by["CHND Trung Hoa"][2024], 60878, 0.5)
        else:
            expect("imports 2024", by["TỔNG SỐ"][2024], 381304, 0.5)
            expect("imports 2025", by["TỔNG SỐ"][2025], 454926, 0.5)
            expect("imports from Korea 2024", by["Hàn Quốc"][2024], 55985, 0.5)
        write_csv(rel, "\n".join([
            f"NSO {code} \"{tp.title}\" — unit: {tp.unit}; NSO updated "
            f"{tp.updated[:10]}; {tp.url}",
            f"Merchandise {flow} by partner, US$ millions, customs basis. Long "
            "format: one row per partner and year.",
            "kind: total / bloc / country. The blocs (ASEAN, APEC, EU, OPEC) "
            "OVERLAP each other and the countries: never stack or sum them.",
            "partner is the NSO label as published (NFC). partner_iso3 is this "
            "fetcher's mapping (the NSO publishes no codes): China is",
            "\"CHND Trung Hoa\" and Hong Kong \"ĐKHC Hồng Công (TQ)\"; match on "
            "the ISO3, never on the name.",
            "Blank value = not published for that partner-year. The TỔNG SỐ "
            "rows are asserted equal to V09.01 every year.",
            "status: final / preliminary (Sơ bộ), parsed off the year label. "
            "Official: true."]),
            ["year", "status", "partner", "partner_iso3", "kind",
             f"{flow}_usd_mn"], rows)

    t14, t15 = Table(TRADE, "V09.14"), Table(TRADE, "V09.15")
    f = Frame()
    f.use(t14)
    f.use(t15)
    grid(f, t14, t14.match("Nhóm hàng", [
        ("XUẤT KHẨU", "goods_exports_total"),
        ("Nhiên liệu và khoáng sản", "exp_fuels_minerals"),
        ("Công nghiệp chế biến", "exp_manufactures"),
        ("Hàng nông sản", "exp_agricultural"), ("Hàng lâm sản", "exp_forestry"),
        ("Hàng thủy sản", "exp_fishery"),
        ("Vàng phi tiền tệ", "exp_nonmonetary_gold"),
        ("NHẬP KHẨU", "goods_imports_total"),
        ("Tư liệu sản xuất", "imp_means_of_production"),
        ("Máy móc, thiết bị", "imp_machinery_equipment"),
        ("Nguyên, nhiên, vật liệu", "imp_materials_fuels"),
        ("Hàng tiêu dùng", "imp_consumer_goods"), ("Lương thực", "imp_staple_food"),
        ("Thực phẩm", "imp_foodstuffs"), ("Hàng y tế", "imp_medical"),
        ("Hàng khác", "imp_other"), ("Vàng phi tiền tệ", "imp_nonmonetary_gold")]),
        "Nhóm hàng", suffix="_pct_gdp")
    kinds = t15.match("Loại hình dịch vụ", [
        ("Tổng số", "total"), ("vận tải", "transport"),
        ("bưu chính viễn thông", "post_telecom"), ("du lịch", "travel"),
        ("tài chính", "financial"), ("bảo hiểm", "insurance"),
        ("Chính phủ", "government"), ("Dịch vụ khác", "other")])
    for flab, fcol in t15.match("Giá trị", [("Xuất khẩu", "exp"),
                                            ("Nhập khẩu", "imp")]):
        grid(f, t15, [(l, f"services_{fcol}_{c}") for l, c in kinds],
             "Loại hình dịch vụ", {"Giá trị": flab}, "_usd_mn")
    f.extra["gdp_scale"] = {y: "old" if y < 2010 else "revalued"
                            for y in f.status}
    f.write("trade/trade_by_group_from_gso.csv", """
NSO V09.14: goods exports by group and imports by end use, as % of GDP
(_pct_gdp), for 2005 and 2009-2025 (2006-2008 absent). The ratios inherit
the GDP REVALUATION in their denominator: 2005 and 2009 are over OLD-scale
GDP, 2010+ over the revalued scale (gdp_scale column); do not draw a ratio
line across 2009->2010 without marking it.
NSO V09.15: services exports and imports by type, US$ millions (_usd_mn),
2005-2025.
""", extra_first=["gdp_scale"])
    return totals


# ---------------------------------------------------------------- markets

RATE_ROWS = [
    ("đồng Việt Nam Không kỳ hạn", "deposit_vnd_demand"),
    ("đồng Việt Nam Kỳ hạn 3 tháng", "deposit_vnd_3m"),
    ("đồng Việt Nam Kỳ hạn 6 tháng", "deposit_vnd_6m"),
    ("đồng Việt Nam Kỳ hạn 12 tháng", "deposit_vnd_12m"),
    ("đồng Việt Nam Kỳ hạn từ trên 12 tháng đến 24", "deposit_vnd_12_24m"),
    ("đồng Việt Nam Kỳ hạn trên 24", "deposit_vnd_over_24m"),
    ("đô la Mỹ Không kỳ hạn", "deposit_usd_demand"),
    ("đô la Mỹ Kỳ hạn 3 tháng", "deposit_usd_3m"),
    ("đô la Mỹ Kỳ hạn 6 tháng", "deposit_usd_6m"),
    ("đô la Mỹ Kỳ hạn 12 tháng", "deposit_usd_12m"),
    ("đô la Mỹ Kỳ hạn từ trên 12 tháng đến 24", "deposit_usd_12_24m"),
    ("đô la Mỹ Kỳ hạn trên 24", "deposit_usd_over_24m"),
    ("cho vay bình quân bằng đồng Việt Nam Ngắn hạn", "lending_vnd_short"),
    ("cho vay bình quân bằng đồng Việt Nam Trung hạn và dài hạn",
     "lending_vnd_medium_long"),
    ("cho vay bình quân bằng đô la Mỹ Ngắn hạn", "lending_usd_short"),
    ("cho vay bình quân bằng đô la Mỹ Trung hạn và dài hạn",
     "lending_usd_medium_long"),
    ("Tỷ giá trung tâm", "central_rate_vnd_per_usd"),
]


def markets() -> None:
    t = Table(NA, "V03.21")
    f = Frame()
    f.use(t)
    grid(f, t, t.match("Chỉ tiêu", RATE_ROWS), "Chỉ tiêu")
    for col, y, v in [("deposit_vnd_12m", 2020, 6.81), ("deposit_vnd_12m", 2024, 4.91),
                      ("deposit_vnd_12m", 2025, 5.13),
                      ("lending_vnd_medium_long", 2020, 10.25),
                      ("lending_vnd_medium_long", 2025, 8.30),
                      ("central_rate_vnd_per_usd", 2020, 23208.78),
                      ("central_rate_vnd_per_usd", 2024, 24170.41),
                      ("central_rate_vnd_per_usd", 2025, 24977.20)]:
        expect(f"{col} {y}", f.get(col, y), v)
    # USD deposit rates are capped at 0% by the SBV since late 2015: real
    # zeros, which must survive as 0 and not become blanks.
    for col in [c for c in f.cols if c.startswith("deposit_usd")]:
        for y in range(2016, 2026):
            expect(f"{col} {y} (SBV 0% cap)", f.get(col, y), 0.0, 1e-9)
    f.write("markets/rates_fx_from_gso.csv", """
NSO V03.21 (Lãi suất, tỷ giá trung tâm), source of record the State Bank
of Vietnam. Annual averages, % a year: VND and USD deposit rates by tenor,
VND and USD lending rates (short; medium and long). Central rate in VND per
US$ (a managed reference; banks trade within a band around it, +/-5% since
October 2022). THE USD DEPOSIT RATES ARE 0 AND THAT IS REAL: the SBV has
capped them at 0% since late 2015. The central rate is blank for 2015-2017
in the table. No policy rate here (SOURCES.yaml meta.pending).
""")

    t = Table(NA, "V03.26")
    f = Frame()
    f.use(t)
    grid(f, t, t.match("Chỉ tiêu chủ yếu", [
        ("vốn hóa thị trường cổ phiếu (Tỷ đồng)", "equity_mcap_vnd_bn"),
        ("Tốc độ tăng giá trị vốn hóa", "equity_mcap_growth_pct"),
        ("Tỷ lệ vốn hóa thị trường cổ phiếu so với", "equity_mcap_pct_gdp"),
        ("Quy mô thị trường trái phiếu (Tỷ đồng)", "bond_market_vnd_bn"),
        ("Quy mô thị trường trái phiếu so với", "bond_market_pct_gdp"),
        ("Tốc độ tăng quy mô thị trường trái phiếu", "bond_market_growth_pct")]),
        "Chỉ tiêu chủ yếu")
    f.write("markets/market_cap_from_gso.csv", """
NSO V03.26 (Hoạt động chứng khoán), source of record the State Securities
Commission. Equity market capitalisation and bond market size in bn VND
(tỷ đồng), their % of GDP and growth in %. 2018-2025 only. Year-end stocks.
""")


# ---------------------------------------------------------------- credit

def credit(gdp_bn: dict) -> None:
    t = Table(NA, "V03.19")
    f = Frame()
    f.use(t)
    meas = t.match("Phân loại", [("Trị giá (Nghìn tỷ đồng)", "vnd_tn"),
                                 ("Tốc độ tăng (%)", "growth_pct")])
    cur = t.match("Chỉ tiêu chủ yếu", [("Số dư", "total"),
                                       ("Bằng đồng Việt Nam", "vnd"),
                                       ("Bằng ngoại tệ", "fx")])
    ten = t.match("Kỳ hạn", [("Tổng số", "all"), ("Ngắn hạn", "short"),
                             ("Trung và dài hạn", "medium_long")])
    for ml, mc in meas:
        for cl, cc in cur:
            for tl, tc in ten:
                f.add(f"credit_{cc}_{tc}_{mc}",
                      t.series(**{"Phân loại": ml, "Chỉ tiêu chủ yếu": cl,
                                  "Kỳ hạn": tl}), t, f"{ml} / {cl} / {tl}")
    for y, v in {2015: 4655.9, 2020: 9192.6, 2024: 15619.5, 2025: 18598.0}.items():
        expect(f"credit {y}", f.get("credit_total_all_vnd_tn", y), v)
    expect("credit 2025 % of V03.01 GDP",
           100 * f.get("credit_total_all_vnd_tn", 2025) * 1000 / gdp_bn[2025],
           145, 1.5)
    f.write("credit/credit_from_gso.csv", """
NSO V03.19: credit outstanding of credit institutions and foreign bank
branches at 31 DECEMBER (dư nợ tín dụng), source of record the State Bank of
Vietnam. Values in THOUSAND bn VND (nghìn tỷ đồng = VND tn); growth in %
y/y. By currency (VND / foreign currency) and tenor (short / medium and
long). A year-end STOCK, never summed. Credit to the whole economy: there is
no household-debt series for Vietnam. 2025 is about 145% of 2025 GDP
(asserted against V03.01).
""")


# ---------------------------------------------------------------- BoP

BOP_ROWS = [
    ("CÁN CÂN VÃNG LAI", "current_account"), ("Cán cân hàng hóa", "goods_balance"),
    ("Xuất khẩu (FOB)", "goods_exports_fob"), ("Nhập khẩu (FOB)", "goods_imports_fob"),
    ("Dịch vụ", "services_balance"), ("Dịch vụ - Xuất khẩu", "services_exports"),
    ("Dịch vụ - Nhập khẩu", "services_imports"), ("Thu nhập", "primary_income_balance"),
    ("Thu nhập - Thu", "primary_income_credit"), ("Thu nhập - Chi", "primary_income_debit"),
    ("Chuyển giao vãng lai", "secondary_income_balance"),
    ("Chuyển giao vãng lai - Thu", "secondary_income_credit"),
    ("Chuyển giao vãng lai - Chi", "secondary_income_debit"),
    ("Tỷ lệ cán cân vãng lai so với", "current_account_pct_gdp"),
    ("CÁN CÂN TÀI CHÍNH", "financial_account"), ("Đầu tư trực tiếp", "fdi_net"),
    ("Đầu tư trực tiếp của Việt Nam ra nước ngoài", "fdi_outward"),
    ("Đầu tư trực tiếp của nước ngoài vào Việt Nam", "fdi_inward"),
    ("Đầu tư gián tiếp", "portfolio_net"),
    ("Đầu tư gián tiếp của Việt Nam ra nước ngoài", "portfolio_outward"),
    ("Đầu tư gián tiếp vào Việt Nam", "portfolio_inward"),
    ("Đầu tư khác (Tài sản có)", "other_investment_assets"),
    ("(Tài sản có) - Tiền và tiền gửi", "other_investment_assets_currency_deposits"),
    ("(Tài sản có) - Các khoản phải thu", "other_investment_assets_other"),
    ("Đầu tư khác (Tài sản nợ)", "other_investment_liabilities"),
    ("(Tài sản nợ) - Tiền và tiền gửi",
     "other_investment_liabilities_currency_deposits"),
    ("Vay, trả nợ nước ngoài", "other_investment_liabilities_loans"),
    ("quyền rút vốn đặc biệt", "other_investment_liabilities_sdr_allocation"),
    ("Đầu tư khác (Ròng)", "other_investment_net"),
    ("LỖI VÀ SAI SÓT", "errors_omissions"), ("CÁN CÂN TỔNG THỂ", "overall_balance"),
    ("DỰ TRỮ VÀ CÁC HẠNG MỤC LIÊN QUAN", "reserves_related_items"),
    ("Tài sản dự trữ", "reserve_assets"),
]


def bop(totals: dict) -> None:
    t = Table(NA, "V03.20")
    f = Frame()
    f.use(t)
    (val, _), = t.match("Phân loại", [("Triệu đô la Mỹ", "")])
    grid(f, t, t.match("Chỉ tiêu chủ yếu", BOP_ROWS), "Chỉ tiêu chủ yếu",
         {"Phân loại": val})
    expect("current account 2024", f.get("current_account", 2024), 30385, 0.5)
    expect("current account 2025", f.get("current_account", 2025), 33135, 0.5)
    expect("transfers credit 2024", f.get("secondary_income_credit", 2024), 16998, 0.5)
    expect("transfers credit 2025", f.get("secondary_income_credit", 2025), 19766, 0.5)
    # Second source: FOB goods exports against the customs total, within 3%.
    for y in range(2018, 2026):
        fob, cus = f.get("goods_exports_fob", y), totals["exports"].get(y)
        if fob is None or cus is None or abs(fob / cus - 1) > 0.03:
            raise RuntimeError(f"BoP goods exports {y} {fob} vs customs {cus}")
    f.write("international/bop_from_gso.csv", """
NSO V03.20 (Cán cân thanh toán quốc tế), source of record the State Bank of
Vietnam. US$ millions, except current_account_pct_gdp (%). 2018-2025 only.
Signs as published by the SBV. secondary_income_credit (current transfers
received) INCLUDES remittances but is not only remittances: a labelled
superset. goods_exports_fob is asserted within 3% of the customs total
(trade_totals_from_gso.csv) every year.
""")


# ---------------------------------------------------------------- social

SEX_AREA = [("Tổng số", "total"), ("Nam", "male"), ("Nữ", "female"),
            ("Thành thị", "urban"), ("Nông thôn", "rural")]


def labour() -> None:
    f = Frame()
    t = Table(POP, "V02.35")
    f.use(t)
    (lf, _), _ = t.match("Cách tính", [("Tổng số (Nghìn người)", ""),
                                       ("Cơ cấu (%)", "")])
    grid(f, t, [(l, f"labour_force_{c}") for l, c in t.match("Phân tổ", SEX_AREA)],
         "Phân tổ", {"Cách tính": lf}, "_thousand")
    t = Table(POP, "V02.39")
    f.use(t)
    (emp, _), (ratio, _) = t.match("Chỉ tiêu", [("Tổng số - Nghìn người", ""),
                                                ("Tỷ lệ so với dân số", "")])
    sa = t.match("Phân tổ", SEX_AREA)
    grid(f, t, [(l, f"employed_{c}") for l, c in sa], "Phân tổ",
         {"Chỉ tiêu": emp}, "_thousand")
    grid(f, t, [(l, f"employed_{c}") for l, c in sa], "Phân tổ",
         {"Chỉ tiêu": ratio}, "_pct_of_population")
    t = Table(POP, "V02.42")
    f.use(t)
    (num, _), (sh, _) = t.match("Phân tổ", [("Tổng số (Nghìn người)", ""),
                                            ("Cơ cấu (%)", "")])
    labs = t.dim("Ngành")
    for frag, col in [("Nông nghiệp, lâm nghiệp và thủy sản", "agriculture"),
                      ("Công nghiệp chế biến, chế tạo", "manufacturing"),
                      ("Xây dựng", "construction")]:
        lab = next(l for l in labs if l.startswith(frag))
        f.add(f"employed_{col}_thousand",
              t.series(**{"Ngành": lab, "Phân tổ": num}), t, lab)
        f.add(f"employed_{col}_share_pct",
              t.series(**{"Ngành": lab, "Phân tổ": sh}), t, lab)
    t = Table(POP, "V02.46")
    f.use(t)
    (inf, _), = t.match("Chỉ tiêu", [("phi chính thức", "")])
    grid(f, t, [(l, f"informal_{c}") for l, c in t.match("Phân tổ", SEX_AREA)],
         "Phân tổ", {"Chỉ tiêu": inf}, "_pct")
    t = Table(POP, "V02.59")
    f.use(t)
    area = t.match("Thành thị, nông thôn", [("CẢ NƯỚC", "national"),
                                            ("Thành thị", "urban"),
                                            ("Nông thôn", "rural")])
    reg = t.match("Vùng", [("Tổng số", "all")] + REGIONS)
    for al, ac in area:
        f.add(f"unemployment_{ac}_pct",
              t.series(**{"Thành thị, nông thôn": al, "Vùng": reg[0][0]}), t, al)
    for rl, rc in reg[1:]:
        f.add(f"unemployment_{rc}_pct",
              t.series(**{"Thành thị, nông thôn": area[0][0], "Vùng": rl}), t, rl)
    for y, v in {2010: 2.91, 2020: 2.48, 2021: 3.20, 2025: 2.21}.items():
        expect(f"unemployment {y}", f.get("unemployment_national_pct", y), v)
    # Door 1 cross-check: the API's 2-dp rounding is harmless for a rate.
    api = api_table(POP, "V02.59")
    for y, (lab, _, _) in t.years.items():
        a = api.get(("CẢ NƯỚC", "Tổng số", lab))
        if a in (None, "", ".", ".."):
            raise RuntimeError(f"API V02.59 {lab}: no national value")
        expect(f"V02.59 {y} HTML vs API", f.get("unemployment_national_pct", y),
               float(a), 0.0051)
    f.write("social/labour_from_gso.csv", """
NSO Labour Force Survey tables. labour_force_* (V02.35): labour force aged
15+, thousand people. employed_* (V02.39): employed people, thousand, and as
% of population; employed_<sector>_* (V02.42): employed by sector, thousand
and share of all employed (%). informal_* (V02.46): informal employment
rate, % of the employed, 2013-2025. unemployment_* (V02.59): unemployment
rate IN WORKING AGE (trong độ tuổi lao động), %, 2010-2025: the NSO
definition, not ADB's 15+ (LUR_PT) or the World Bank's ILO-modelled
SL.UEM.TOTL.ZS; three lines, never one. Fetched through the HTML door at
full precision; the JSON API's rounded copy of V02.59 is asserted equal to
two decimals.
""")


QUINTILE_GROUPS = [("CẢ NƯỚC", "national"), ("Thành thị", "urban"),
                   ("Nông thôn", "rural"), ("Giới tính chủ hộ - Nam", "head_male"),
                   ("Giới tính chủ hộ - Nữ", "head_female")] + REGIONS


def income_quintiles() -> None:
    t = Table(SOCIAL, "V14.29")
    groups = t.match("Phân tổ", QUINTILE_GROUPS)
    qs = t.match("Nhóm thu nhập", [("Bình quân chung", "average"),
                                   ("Nhóm 1", "q1"), ("Nhóm 2", "q2"),
                                   ("Nhóm 3", "q3"), ("Nhóm 4", "q4"),
                                   ("Nhóm 5", "q5")])
    rows = []
    for gl, gc in groups:
        sers = [t.series(**{"Phân tổ": gl, "Nhóm thu nhập": ql}) for ql, _ in qs]
        for y in sorted(t.years):
            rows.append([y, t.years[y][1], gc, gl, *[fmt(s[y]) for s in sers]])
    nat = {y: r for y, r in ((r[0], r) for r in rows if r[2] == "national")}
    for y, r in nat.items():
        q = [float(x) for x in r[5:]]
        if q != sorted(q):
            raise RuntimeError(f"V14.29 {y}: quintiles not increasing {q}")
    write_csv("social/income_quintiles_from_gso.csv", "\n".join([
        f"NSO V14.29 \"{t.title}\" — unit: {t.unit}; NSO updated "
        f"{t.updated[:10]}; {t.url}",
        "Monthly income per person at CURRENT prices, thousand VND (nghìn "
        "đồng), from the VHLSS household survey: the average and quintiles "
        "1 (poorest) to 5.",
        "One row per breakdown (breakdown_vi is the NSO label, NFC) and year. "
        "Survey years 2010, 2012, 2014, 2016, then annual 2018-2025: the gaps "
        "are survey gaps, never interpolated. Nominal: compare ratios, not "
        "levels, across years.",
        "status: final / preliminary (Sơ bộ). Official: true."]),
        ["year", "status", "breakdown", "breakdown_vi",
         *[c for _, c in qs]], rows)


GINI_GROUPS = [("CẢ NƯỚC", "national"), ("Thành thị", "urban"),
               ("Nông thôn", "rural")] + REGIONS


def gini() -> None:
    t = Table(SOCIAL, "V14.38")
    f = Frame()
    f.use(t)
    for lab, col in t.match("Phân tổ", GINI_GROUPS):
        f.split(f"gini_{col}", t.series(**{"Phân tổ": lab}), t, lab, 2020,
                "2002_2019", "2020_on")
    nat = {**f.cols["gini_national_2002_2019"], **f.cols["gini_national_2020_on"]}
    for y, v in {2006: 0.424, 2010: 0.433, 2018: 0.425, 2019: 0.423,
                 2020: 0.375, 2025: 0.323}.items():
        expect(f"Gini {y}", nat[y], v)
    if nat[2019] - nat[2020] < 0.03:
        raise RuntimeError("Gini 2019->2020 step is gone: revisit the split")
    f.write("social/gini_from_gso.csv", """
NSO V14.38: income Gini coefficient (0-1 scale) from the VHLSS, national,
urban/rural and six regions; survey years 2002-2018 biennial, then annual.
UNDOCUMENTED STEP: the national Gini falls from 0.423 (2019) to 0.375
(2020), five points in a year, with no footnote in the table; a VHLSS
income-module or weighting change is the likely cause, unverified. Every
column is therefore split into _2002_2019 and _2020_on and the two segments
are never joined. The World Bank's SI.POV.GINI is a consumption Gini on a
0-100 scale, a different quantity in its own file.
""")


POVERTY_GROUPS = [("CẢ NƯỚC", "national"), ("Dân tộc Kinh/Hoa", "kinh_hoa"),
                  ("Dân tộc khác", "other_ethnic"), ("Thành thị", "urban"),
                  ("Nông thôn", "rural")] + REGIONS


def poverty(v1401_poverty: dict) -> None:
    t = Table(SOCIAL, "V14.46")
    note = px_notex(SOCIAL, "V14.46")
    if "2016-2021" not in note or "2022-2025" not in note:
        raise RuntimeError(f"V14.46: poverty-standard NOTEX gone: {note!r}")
    f = Frame()
    f.use(t)
    grid(f, t, [(l, f"poverty_{c}_pct") for l, c in
                t.match("Phân tổ", POVERTY_GROUPS)], "Phân tổ")
    f.extra["year_label"] = {y: lab for y, (lab, _, _) in t.years.items()}
    f.extra["standard"] = {
        y: ("income-based (pre-2016 national line)" if y <= 2016 else
            "multidimensional 2016-2021" if y <= 2021 else
            "multidimensional 2022-2025") for y in t.years}
    p = f.cols["poverty_national_pct"]
    for y, v in {2006: 15.5, 2010: 14.2, 2015: 7.0, 2016: 5.8, 2020: 4.8,
                 2023: 3.37, 2024: 2.3, 2025: 1.35}.items():
        expect(f"poverty {y}", p[y], v)
    absent("V14.46 2017-2019", {y: 1 for y in t.years}, [2017, 2018, 2019])
    # The second table disagrees on 2016 because it uses the new standard.
    expect("V14.01 poverty 2016", v1401_poverty[2016], 9.2)
    f.write("social/poverty_from_gso.csv", """
NSO V14.46: share of HOUSEHOLDS below the government's poverty standard, %,
national, by ethnicity, urban/rural and region. The standard is redefined
every five years. PX NOTEX (asserted present): "*" multidimensional
standard 2016-2021, "**" multidimensional standard 2022-2025, and from 2022
the 2022-2025 standard. year_label keeps the markers exactly as published
("2021*", "2023**"); `standard` is this fetcher's reading of the NOTEX: up
to 2016 income-based (V14.46 keeps 2016 on the old line: 5.8, where the
summary table V14.01 reads 9.2 on the multidimensional standard), 2020-2021
the 2016-2021 multidimensional standard, 2022+ the 2022-2025 standard.
2017-2019 are absent from this table. The standards are never spliced: draw
one segment per standard, and keep V14.01 (hdi_from_gso.csv) a separate line.
""", extra_first=["year_label", "standard"])


HDI_ROWS = [
    ("Dân số trung bình (Nghìn người)", "population_avg_thousand"),
    ("dưới 16 tuổi", "population_under16_thousand"),
    ("dưới 18 tuổi", "population_under18_thousand"),
    ("Chỉ số phát triển con người", "hdi_nso"),
    ("Tuổi thọ trung bình", "life_expectancy_years"),
    ("Số năm đi học bình quân", "mean_years_schooling"),
    ("Số năm đi học kỳ vọng", "expected_years_schooling"),
    ("Thu nhập quốc gia bình quân đầu người", "gni_pc_vnd_mn"),
    ("Thu nhập bình quân đầu người một tháng", "income_pc_month_vnd_thousand"),
    ("Hệ số GINI", "gini"),
    ("Chi tiêu bình quân đầu người một tháng", "expenditure_pc_month_vnd_thousand"),
    ("Tỷ lệ hộ nghèo", "poverty_households_pct"),
    ("Giường bệnh bình quân 1 vạn dân", "hospital_beds_per_10k"),
    ("Bác sĩ bình quân 1 vạn dân", "doctors_per_10k"),
    ("nguồn nước hợp vệ sinh", "hygienic_water_pct"),
    ("dùng điện sinh hoạt", "electricity_pct"),
    ("đồ dùng lâu bền", "durables_pct"),
    ("Diện tích nhà ở bình quân", "housing_m2_per_person"),
]


def hdi() -> dict:
    t = Table(SOCIAL, "V14.01")
    f = Frame()
    f.use(t)
    grid(f, t, t.match("Chỉ tiêu", HDI_ROWS), "Chỉ tiêu")
    for y, v in {2010: 0.649, 2019: 0.703, 2023: 0.746, 2024: 0.752,
                 2025: 0.765}.items():
        expect(f"NSO HDI {y}", f.get("hdi_nso", y), v)
    absent("NSO HDI before 2010", f.cols["hdi_nso"], [2006, 2008])
    for y, v in {2016: 9.2, 2017: 7.9, 2018: 6.84, 2019: 5.65}.items():
        expect(f"V14.01 poverty {y}", f.get("poverty_households_pct", y), v)
    f.write("international/hdi_from_gso.csv", """
NSO V14.01 (Một số chỉ tiêu xã hội chủ yếu): the NSO's OWN Human
Development Index computed from national inputs, with the other headline
social indicators of the summary table. Units are in the column names.
hdi_nso is NOT the UNDP HDI (UNDP reads 2023 = 0.766 against 0.746 here):
two publishers, two lines, never spliced. HDI is blank before 2010.
poverty_households_pct here is the SUMMARY table's series, which puts 2016
on the multidimensional standard (9.2) and carries 2017-2019; the regional
table V14.46 (social/poverty_from_gso.csv) disagrees on 2016 (5.8). Two
tables, two lines.
""")
    return {"poverty": f.cols["poverty_households_pct"],
            "population": f.cols["population_avg_thousand"]}


# ---------------------------------------------------------------- demography

def population(gdp: dict, hdi_pop: dict) -> dict:
    t = Table(POP, "V02.02")
    f = Frame()
    f.use(t)
    meas = t.match("Cách tính", [("Tổng số (Nghìn người)", "thousand"),
                                 ("Tỷ lệ tăng", "growth_pct"),
                                 ("Cơ cấu", "share_pct")])
    sa = t.match("Phân tổ", SEX_AREA)
    for ml, mc in meas:
        grid(f, t, [(l, f"population_{c}") for l, c in sa], "Phân tổ",
             {"Cách tính": ml}, f"_{mc}")
    pop = f.cols["population_total_thousand"]
    for y, v in {2006: 83311.2, 2019: 96484.0, 2023: 100309.21,
                 2024: 101343.75}.items():
        expect(f"population {y}", pop[y], v)
    # Door 1 cross-check: thousands to the API's rounding.
    api = api_table(POP, "V02.02")
    for y, (lab, _, _) in t.years.items():
        a = api.get((meas[0][0], lab, "Tổng số"))
        if a in (None, "", ".", ".."):
            raise RuntimeError(f"API V02.02 {lab}: no total")
        expect(f"V02.02 {y} HTML vs API", pop[y], float(a), 0.051)
    # V14.01's population agrees with this table to its rounding except at
    # 2014 (90,728.9 vs 91,203.8, an older vintage) and 2022 (99,461.7 vs
    # 99,467.9).
    for y in (2019, 2020, 2024):
        expect(f"V02.02 vs V14.01 population {y}", hdi_pop[y], pop[y], 0.51)
    # Second source: GDP per person (US$) x population against the World
    # Bank's current-US$ GDP, and US$ GDP from the VND level at the SBV
    # central rate; both within 2%.
    _, _, blob = _request("https://api.worldbank.org/v2/country/VNM/indicator/"
                          "NY.GDP.MKTP.CD?format=json&date=2024")
    rows = json.loads(blob)[1]
    wb = next(r["value"] for r in rows if r["date"] == "2024")
    implied = gdp["gdp_pc_usd"][2024] * pop[2024] * 1e3
    if abs(implied / wb - 1) > 0.02:
        raise RuntimeError(f"GDP 2024: NSO implies US${implied/1e9:.1f}bn, "
                           f"World Bank US${wb/1e9:.1f}bn")
    print(f"  cross-check: NSO GDP 2024 = US${implied/1e9:.1f}bn "
          f"(per person x population), World Bank US${wb/1e9:.1f}bn")
    f.write("demography/population_from_gso.csv", """
NSO V02.02: AVERAGE annual population (dân số trung bình), thousand people,
by sex and urban/rural; growth in % y/y and structure (share of the total)
in %. 1990-2025. Not the UN WPP mid-year estimate the World Bank carries
(2024 101.0mn against 101.34mn here). The 2009 and 2019 censuses re-based
the intercensal estimates, so growth across those years is within-vintage
only. Fetched through the HTML door; the JSON API's copy is asserted equal
to its rounding, and V14.01's population column is asserted equal for
2019, 2020 and 2024. V14.01 differs from this file at 2014 (90,728.9 vs
91,203.8, an older vintage) and 2022 (99,461.7 vs 99,467.9); 2015-2018
agree to its rounding.
Cross-check: 2024 GDP per person (US$, V03.01) x this population is within
2% of the World Bank's current-US$ GDP.
""")
    return pop


def vitals() -> None:
    f = Frame()
    t = Table(POP, "V02.11")
    f.use(t)
    area = t.match("Thành thị/nông thôn", [("TỔNG SỐ", "total"),
                                           ("Thành thị", "urban"),
                                           ("Nông thôn", "rural")])
    for rl, rc in t.match("Tỷ suất", [("Tỷ suất sinh thô", "cbr"),
                                      ("Tỷ suất chết thô", "cdr"),
                                      ("Tỷ lệ tăng tự nhiên", "natural_increase")]):
        grid(f, t, [(l, f"{rc}_{c}") for l, c in area], "Thành thị/nông thôn",
             {"Tỷ suất": rl}, "_per_mille")
    t = Table(POP, "V02.15")
    f.use(t)
    grid(f, t, [(l, f"tfr_{c}") for l, c in t.match("Phân tổ", [
        ("Tổng số", "total"), ("Thành thị", "urban"), ("Nông thôn", "rural")])],
        "Phân tổ")
    t = Table(POP, "V02.17")
    f.use(t)
    sa = t.match("Phân tổ", SEX_AREA)
    for rl, rc in t.match("Tỷ suất", [("dưới một tuổi", "imr"),
                                      ("dưới năm tuổi", "u5mr")]):
        grid(f, t, [(l, f"{rc}_{c}") for l, c in sa], "Phân tổ",
             {"Tỷ suất": rl}, "_per_1000_live_births")
    for col, y, v in [("cbr_total_per_mille", 2006, 17.4),
                      ("cbr_total_per_mille", 2024, 13.5),
                      ("cdr_total_per_mille", 2006, 5.3),
                      ("cdr_total_per_mille", 2019, 6.32),
                      ("cdr_total_per_mille", 2025, 6.1),
                      ("tfr_total", 2006, 2.09), ("tfr_total", 2019, 2.09),
                      ("tfr_total", 2023, 1.96), ("tfr_total", 2024, 1.91),
                      ("tfr_total", 2025, 1.93)]:
        expect(f"{col} {y}", f.get(col, y), v)
    if all(float(v).is_integer() for v in f.cols["tfr_total"].values()):
        raise RuntimeError("TFR came back rounded: wrong door?")
    f.write("demography/vital_rates_from_gso.csv", """
NSO, from the annual Population Change and Family Planning survey (not
civil registration). V02.11: crude birth rate, crude death rate and rate of
natural increase, per mille (‰), total/urban/rural. V02.15: total fertility
rate, children per woman, FULL PRECISION from the HTML JSON-stat door (the
JSON API rounds every year to "2"). V02.17: infant and under-5 mortality,
deaths per 1,000 live births, by sex and urban/rural. 2001-2025.
""")


def life_expectancy() -> None:
    t = Table(POP, "V02.24")
    f = Frame()
    f.use(t)
    grid(f, t, [(l, f"life_expectancy_{c}") for l, c in t.match(
        "Giới tính, thành thị, nông thôn và vùng",
        [("CẢ NƯỚC", "national"), ("Nam", "male"), ("Nữ", "female"),
         ("Thành thị", "urban"), ("Nông thôn", "rural")] + REGIONS)],
        "Giới tính, thành thị, nông thôn và vùng", suffix="_years")
    le = f.cols["life_expectancy_national_years"]
    for y, v in {2010: 72.9, 2020: 73.7, 2021: 73.64, 2022: 73.64, 2023: 74.5,
                 2024: 74.7, 2025: 74.7}.items():
        expect(f"life expectancy {y}", le[y], v)
    if le[2021] != le[2022]:
        raise RuntimeError("life expectancy 2021 != 2022: the carried-value "
                           "note no longer applies")
    absent("V02.24 2006-2008", {y: 1 for y in t.years}, [2006, 2007, 2008])
    f.write("demography/life_expectancy_from_gso.csv", """
NSO V02.24: life expectancy at birth, years, national, by sex, urban/rural
and region. Years 2005, 2009-2025 (2006-2008 absent).
FLAG: 2021 and 2022 are IDENTICAL to the hundredth (73.64), a probable
CARRIED VALUE rather than a COVID-year measurement; annotate it and do not
read a 2021-2022 plateau into it. WHO and World Bank figures are modelled,
disagree with this and with each other, and belong in their own files.
""")


# ---------------------------------------------------------------- security

JUSTICE_ROWS = [
    ("Số vụ án đã khởi tố", "cases_prosecuted"),
    ("Số bị can đã khởi tố", "defendants_prosecuted"),
    ("Số nữ bị can đã khởi tố", "female_defendants_prosecuted"),
    ("Số vụ án đã truy tố", "cases_indicted"),
    ("Số bị can đã truy tố", "defendants_indicted"),
    ("Số nữ bị can đã truy tố", "female_defendants_indicted"),
    ("Số vụ án đã xét xử", "cases_tried"),
    ("Số bị cáo đã xét xử", "defendants_tried"),
    ("Số nữ bị cáo đã xét xử", "female_defendants_tried"),
    ("trợ giúp pháp lý (Lượt người)(*)", "legal_aid_persons"),
    ("Số nữ được trợ giúp pháp lý", "female_legal_aid_persons"),
    ("thi hành xong về việc", "civil_judgments_cases_completed_pct"),
    ("thi hành xong về tiền", "civil_judgments_money_completed_pct"),
    ("Số luật sư bình quân", "lawyers_per_10k"),
]
CRIME_GROUPS = [
    ("CẢ NƯỚC", "all"), ("an ninh quốc gia", "national_security"),
    ("tính mạng, sức khỏe", "life_health_dignity"),
    ("quyền tự do", "freedoms_democratic_rights"), ("sở hữu", "property"),
    ("hôn nhân và gia đình", "marriage_family"),
    ("trật tự quản lý kinh tế", "economic_management"),
    ("môi trường", "environment"), ("ma túy", "drugs"),
    ("an toàn công cộng", "public_safety_order"),
    ("trật tự quản lý hành chính", "administrative_order"),
    ("chức vụ", "official_duty"), ("hoạt động tư pháp", "judicial_activity"),
]


def justice() -> None:
    t = Table(SOCIAL, "V14.77")
    f = Frame()
    f.use(t)
    grid(f, t, t.match("Phân tổ", JUSTICE_ROWS), "Phân tổ")
    t78 = Table(SOCIAL, "V14.78")
    f.use(t78)
    meas = t78.match("Chỉ tiêu", [("Điều luật", "article"),
                                  ("Số vụ án đã bị khởi tố", "cases"),
                                  ("Số bị can đã bị khởi tố", "defendants")])
    for gl, gc in t78.match("Phân tổ", CRIME_GROUPS):
        for ml, mc in meas[1:]:   # "Điều luật" is the Penal Code article number
            f.add(f"prosecuted_{mc}_{gc}",
                  t78.series(**{"Phân tổ": gl, "Chỉ tiêu": ml}), t78,
                  f"{gl} / {ml}")
    c = f.cols["cases_prosecuted"]
    for y, v in {2011: 71665, 2024: 100504, 2025: 79791}.items():
        expect(f"cases prosecuted {y}", c[y], v, 0.5)
    expect("cases tried 2013", f.get("cases_tried", 2013), 67779, 0.5)
    expect("cases tried 2024", f.get("cases_tried", 2024), 81125, 0.5)
    expect("V14.78 national = V14.77 2025", f.get("prosecuted_cases_all", 2025),
           c[2025], 0.5)
    f.write("security/justice_from_gso.csv", """
NSO V14.77 (Hoạt động tư pháp), source of record the Supreme People's
Procuracy and Supreme People's Court: cases and defendants PROSECUTED
(khởi tố), indicted (truy tố) and tried (xét xử), counts; legal aid, persons;
civil-judgment completion rates, %; lawyers per 10,000 people. 2011-2025.
These count what the justice system processed, not what happened: a rise is
enforcement as much as crime. The 2025 fall is preliminary and unexplained.
prosecuted_*_<group> (V14.78): prosecutions by Penal Code chapter, cases and
defendants, 2025 ONLY (the 2025 row); its national total is asserted equal
to V14.77. No homicide row exists in any NSO table.
""")


TRAFFIC_ROWS = [
    ("Số vụ tai nạn giao thông (Vụ)", "traffic_accidents"),
    ("Số vụ va chạm giao thông", "traffic_minor_collisions"),
    ("từ ít nghiêm trọng trở lên", "traffic_accidents_less_serious_or_worse"),
    ("Số người chết do tai nạn giao thông", "traffic_deaths"),
    ("Số người bị thương do tai nạn giao thông", "traffic_injuries"),
    ("Số vụ cháy, nổ", "fires_explosions"),
    ("Số người chết do cháy, nổ", "fire_deaths"),
    ("Số người bị thương do cháy, nổ", "fire_injuries"),
    ("thiệt hại ước tính do cháy nổ (Tỷ đồng)", "fire_damage_vnd_bn"),
]
SPLIT_TRAFFIC = {"traffic_accidents", "traffic_deaths", "traffic_injuries"}


def traffic() -> None:
    t = Table(SOCIAL, "V14.86")
    f = Frame()
    f.use(t)
    for lab, col in t.match("Phân tổ", TRAFFIC_ROWS):
        ser = t.series(**{"Phân tổ": lab})
        if col in SPLIT_TRAFFIC:
            f.split(col, ser, t, lab, 2022, "to2021", "from2022")
        else:
            f.add(col, ser, t, lab)
    d = {**f.cols["traffic_deaths_to2021"], **f.cols["traffic_deaths_from2022"]}
    for y, v in {2012: 9838, 2021: 5790, 2022: 13551, 2024: 11205,
                 2025: 10533}.items():
        expect(f"traffic deaths {y}", d[y], v, 0.5)
    expect("accidents 2021", f.get("traffic_accidents_to2021", 2021), 11487, 0.5)
    expect("accidents 2022", f.get("traffic_accidents_from2022", 2022), 23352, 0.5)
    expect("collisions 2021", f.get("traffic_minor_collisions", 2021), 4055, 0.5)
    expect("collisions 2022", f.get("traffic_minor_collisions", 2022), 3490, 0.5)
    if d[2022] / d[2021] < 2:
        raise RuntimeError("traffic-death 2022 step is gone: revisit the split")
    t87 = Table(SOCIAL, "V14.87")
    f.use(t87)
    meas = t87.match("Chỉ tiêu", [("Số Vụ TNGT", "accidents"),
                                  ("Số người chết", "deaths"),
                                  ("Số người bị thương", "injuries")])
    for bl, bc in t87.match("Phân tổ", [
            ("CẢ NƯỚC", "all"), ("Đường bộ", "road"), ("Đường sắt", "rail"),
            ("Đường thủy", "inland_waterway"), ("Đường hàng hải", "maritime")]
            + REGIONS + [("Khác", "other_region")]):
        for ml, mc in meas:
            f.add(f"tngt_{mc}_{bc}", t87.series(**{"Phân tổ": bl, "Chỉ tiêu": ml}),
                  t87, f"{bl} / {ml}")
    # V14.87 does NOT simply break V14.86 down. Its road+rail+waterway+
    # maritime deaths match V14.86 within 3% in 2023 and 2024, but in 2022
    # they sum to the OLD, narrow basis (6,397 against 13,551), so V14.87
    # 2022 sits on the pre-reclassification definition. Its own CẢ NƯỚC row
    # equals the mode sum in 2022-2023 but not in 2024 (3,855 against
    # 11,101): the 2024 national row is internally inconsistent.
    modes = ["road", "rail", "inland_waterway", "maritime"]
    msum = {y: sum(f.get(f"tngt_deaths_{m}", y) or 0 for m in modes)
            for y in (2022, 2023, 2024)}
    for y in (2023, 2024):
        if abs(msum[y] / d[y] - 1) > 0.03:
            raise RuntimeError(f"V14.87 {y} mode deaths {msum[y]} vs V14.86 {d[y]}")
    if msum[2022] > 0.6 * d[2022]:
        raise RuntimeError("V14.87 2022 is no longer on the narrow basis: "
                           "revisit the note")
    for y in (2022, 2023, 2024):
        if f.get("tngt_deaths_all", y) != msum[y]:
            print(f"  NOTE V14.87 {y}: CẢ NƯỚC deaths "
                  f"{f.get('tngt_deaths_all', y)} != sum of modes {msum[y]}")
    f.write("security/traffic_fire_from_gso.csv", """
NSO V14.86 (Trật tự và an toàn xã hội), source of record the Ministry of
Public Security: traffic accidents, collisions, deaths and injuries; fires
and explosions, deaths, injuries and damage (bn VND). Counts. 2012-2025.
DEFINITIONAL BREAK AT 2022, NOT A SAFETY COLLAPSE: accidents double (11,487
-> 23,352) and deaths rise 134% (5,790 -> 13,551) while minor collisions
(va chạm) FALL and stop being reported after 2023. The table carries no
footnote; the fetcher asserts the step. Accidents, deaths and injuries are
therefore split into _to2021 and _from2022, never joined. The police count
is far below the WHO modelled road-death estimate before 2022.
tngt_<measure>_<breakdown> (V14.87): accidents, deaths and injuries by road
type and region, 2022-2024 only. NOT a clean breakdown of V14.86: its 2022
rows are on the OLD narrow basis (mode deaths sum to 6,397 against V14.86's
13,551), its 2023-2024 mode sums match V14.86 within 3% (asserted), and its
own 2024 CẢ NƯỚC row (3,855) does not equal its modes (11,101): use the mode
rows, never tngt_*_all for 2024, and never compare 2022 with 2023 in it.
""")


# ---------------------------------------------------------------- mortality

def registered_deaths() -> None:
    t = Table(POP, "V02.34")
    f = Frame()
    f.use(t)
    if t.dim("Tỉnh, thành phố")[0] != "CẢ NƯỚC":
        raise RuntimeError("V02.34: first row is not CẢ NƯỚC")
    grid(f, t, [(l, f"deaths_registered_{c}") for l, c in t.match(
        "Hạn đăng ký", [("Tổng số", "total"), ("Đúng hạn", "on_time"),
                        ("Quá hạn", "late")])], "Hạn đăng ký",
        {"Tỉnh, thành phố": "CẢ NƯỚC"})
    for y, v in {2019: 556015, 2020: 583751, 2021: 625455, 2022: 725035,
                 2023: 642391, 2024: 629465}.items():
        expect(f"registered deaths {y}", f.get("deaths_registered_total", y), v, 0.5)
    for y in t.years:
        s = f.get("deaths_registered_on_time", y) + f.get("deaths_registered_late", y)
        expect(f"V02.34 {y} on time + late = total", s,
               f.get("deaths_registered_total", y), 1)
    f.write("mortality/registered_deaths_from_gso.csv", """
NSO V02.34: deaths REGISTERED (đăng ký khai tử) in the civil registry,
source of record the Ministry of Justice; national (CẢ NƯỚC) row; total, on
time (đúng hạn) and late (quá hạn), counts, 2018-2024. Registrations land in
the year they are filed, so the 2022 peak lags the 2021 COVID wave; the late
column measures that. No cause of death: Vietnam has no machine-readable
ICD-coded death register.
""")


HIV_ROWS = [
    ("Số người nhiễm HIV - Phát hiện mới", "hiv_new_infections"),
    ("Số bệnh nhân AIDS - Phát hiện mới", "aids_new_cases"),
    ("Số người nhiễm HIV còn sống - Lũy kế", "hiv_living_cumulative"),
    ("Số bệnh nhân AIDS còn sống - Lũy kế", "aids_living_cumulative"),
    ("Số người chết do HIV/AIDS trong năm", "hiv_aids_deaths"),
    ("Số người chết do HIV/AIDS lũy kế", "hiv_aids_deaths_cumulative"),
    ("trên 100.000 dân", "hiv_living_per_100k"),
    ("trong năm 2024 trên 100.000 dân", "hiv_aids_deaths_per_100k"),
]


def hiv() -> None:
    t = Table(SOCIAL, "V14.19")
    f = Frame()
    f.use(t)
    places = t.dim("Địa phương")
    if places[0] != "CẢ NƯỚC" or places[-1] != "Không xác định":
        raise RuntimeError(f"V14.19: unexpected first/last rows")
    rows = t.match("Thông tin", HIV_ROWS)
    grid(f, t, rows, "Thông tin", {"Địa phương": "CẢ NƯỚC"})
    # The national row includes the unknown-province row: regions + unknown
    # must add up to it wherever all are published.
    regions = [p for p in places if any(p.startswith(r) for r, _ in REGIONS)]
    if len(regions) != 6:
        raise RuntimeError(f"V14.19: {len(regions)} region rows")
    new = rows[0][0]
    for y in t.years:
        parts = [t.series(**{"Địa phương": p, "Thông tin": new})[y]
                 for p in regions + ["Không xác định"]]
        nat = f.get("hiv_new_infections", y)
        if nat is not None and None not in parts and abs(sum(parts) - nat) > 1:
            raise RuntimeError(f"V14.19 {y}: regions+unknown {sum(parts)} "
                               f"!= national {nat}")
    f.write("mortality/hiv_from_gso.csv", """
NSO V14.19, source of record the Ministry of Health: national (CẢ NƯỚC) row.
New HIV infections and new AIDS cases detected in the year, people living
with HIV / AIDS (cumulative to 31 December), deaths from HIV/AIDS in the
year and cumulative, counts; per 100,000 people as labelled (the NSO's label
on the death rate names 2024 for every year). 2011-2024. The national row
includes "Không xác định" (unknown province); the fetcher asserts regions +
unknown = national for new infections. The one cause-specific mortality
count the NSO publishes.
""")


# ---------------------------------------------------------------- migration

def internal_migration() -> None:
    t = Table(POP, "V02.21-23")
    dim = "Tỉnh/Thành phố"
    places = t.dim(dim)
    rates = t.match("Tỷ suất", [("nhập cư", "in"), ("xuất cư", "out"),
                                ("di cư thuần", "net")])
    region_names = [r for r, _ in REGIONS]
    rows = []
    for p in places:
        level = ("national" if p == "CẢ NƯỚC" else
                 "region" if any(p.startswith(r) for r in region_names)
                 else "province")
        sers = [t.series(**{dim: p, "Tỷ suất": rl}) for rl, _ in rates]
        for y in sorted(t.years):
            rows.append([y, t.years[y][1], p, level,
                         *[fmt(s[y]) for s in sers]])
    if sum(1 for p in places if any(p.startswith(r) for r in region_names)) != 6:
        raise RuntimeError("V02.21-23: expected six region rows")
    nat_in = t.series(**{dim: "CẢ NƯỚC", "Tỷ suất": rates[0][0]})
    expect("national in-migration 2010", nat_in[2010], 9.7)
    expect("national in-migration 2012", nat_in[2012], 7.2)
    write_csv("migration/internal_migration_from_gso.csv", "\n".join([
        f"NSO V02.21-23 \"{t.title}\" — unit: {t.unit}; NSO updated "
        f"{t.updated[:10]}; {t.url}",
        "INTERNAL migration between provinces, NOT international: "
        "in-migration, out-migration and net migration rates, per mille (‰).",
        "Years 2005, 2007-2025. Long format: one row per place and year; "
        "level = national / region / province; place is the NSO label (NFC).",
        "The provinces are the pre-2025 63-province map plus Hà Tây (merged "
        "into Hà Nội in 2008); the 2025 merger to 34 provinces will re-key "
        "every provincial table.",
        "Blank = not published. status: final / preliminary (Sơ bộ). "
        "Official: true."]),
        ["year", "status", "place", "level", "in_migration_per_mille",
         "out_migration_per_mille", "net_migration_per_mille"], rows)


# ---------------------------------------------------------------- main

def main() -> None:
    print("NSO (Cục Thống kê) PxWeb")
    g = gdp()
    cpi()
    budget(g["gdp_bn"])
    totals = trade()
    markets()
    credit(g["gdp_bn"])
    bop(totals)
    labour()
    income_quintiles()
    gini()
    h = hdi()
    poverty(h["poverty"])
    pop = population(g, h["population"])
    print(f"  population 2024 = {pop[2024] / 1e3:.1f}mn (asserted 101,343.75k)")
    vitals()
    life_expectancy()
    justice()
    traffic()
    registered_deaths()
    hiv()
    internal_migration()
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
