#!/usr/bin/env python3
"""Refresh Japan Customs trade totals into sidecar CSVs.

Usage:  python3 -I countries/japan/fetch/fetch_customs.py

  d41ca.csv      world, calendar-year exports and imports (普通貿易統計)
  d41ma.csv      world, monthly — used ONLY for the running year
  d52caNNN.csv   exports to one partner, calendar year, by commodity
  d62caNNN.csv   imports from one partner, calendar year, by commodity

Every file is linked from the 輸出入総額の推移 index page (time.htm), so
the file names are read from its anchors by their Japanese labels rather
than hardcoded: if Customs renumbers a partner the fetcher fails instead
of silently fetching another country.

Units are ¥ THOUSAND (千円) in every file. The sidecars convert explicitly
to ¥ BILLION (÷ 1,000,000) and say so in their comment lines.

THE ZERO-FILL. d41ma.csv carries every month of the running year, and the
months not yet published are written "0 ,0" — a presence test would count
twelve months in October. A month counts only when both its exports and
imports are non-zero, the zeros must be strictly trailing (a zero in the
middle of the published run is a payload problem and fails), and the
running year is written as a year-to-date with its month count in a
separate column, never as an annual total.

Customs basis means goods only, exports FOB and imports CIF. It is NOT the
balance-of-payments goods account (fetch_boj.py), and the two are never
spliced.

Cross-check: 2024 exports converted at the World Bank's PA.NUS.FCRF
annual-average rate must agree with the World Bank / WTO merchandise
exports figure TX.VAL.MRCH.CD.WT to within 2%.

Outputs: data/trade/trade_from_customs.csv
         data/trade/trade_partners_from_customs.csv
"""
from __future__ import annotations

import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "trade"
CACHE = ROOT / "cache"

BASE = "https://www.customs.go.jp/toukei/suii/html/"
INDEX = BASE + "time.htm"
WB = ("https://api.worldbank.org/v2/country/JPN/indicator/{code}"
      "?format=json&per_page=200&date=2006:2026")
HEADERS = {"User-Agent": "worldreports-data-fetcher/1.0"}

YEAR_FROM = 2006
LAST_FULL_YEAR = 2025          # country.yaml

# (column key, index label of the export file, of the import file)
PARTNERS = [
    ("usa", "米国 年別(輸出）", "米国 年別(輸入）"),
    ("eu", "EU 年別(輸出）", "EU 年別(輸入）"),
    ("asia", "アジア 年別(輸出）", "アジア 年別(輸入）"),
    ("china", "中国 年別(輸出）", "中国 年別(輸入）"),
    ("korea", "韓国 年別(輸出）", "韓国 年別(輸入）"),
    ("asean", "ASEAN 年別(輸出）", "ASEAN 年別(輸入）"),
    ("middle_east", "中東 年別(輸出）", "中東 年別(輸入）"),
    ("russia", "ロシア 年別(輸出）", "ロシア 年別(輸入）"),
]
WORLD_ANNUAL, WORLD_MONTHLY = "世界 年別", "世界 月別"

# Values DISCOVERY.md / SOURCES.yaml verified live on 2026-10-22, in ¥1,000.
MUST_MATCH_WORLD = {
    2006: (75_246_173_392, 67_344_293_072),
    2024: (107_087_511_087, 112_715_960_939),
}
# Partner totals in ¥ trillion, verified on the same day (±0.01tn).
MUST_MATCH_PARTNER = {("usa", "x", 2024): 21.29, ("usa", "x", 2025): 20.37,
                      ("china", "x", 2024): 18.86, ("china", "x", 2025): 18.78}


class FetchError(RuntimeError):
    pass


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise FetchError(msg)


def get(url: str) -> bytes:
    """GET with polite spacing and back-off on 429/403/5xx."""
    last: Exception | None = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=90) as r:
                body = r.read()
            time.sleep(1.0)
            return body
        except urllib.error.HTTPError as e:
            last = e
            if e.code not in (403, 429) and e.code < 500:
                break
        except Exception as e:  # noqa: BLE001
            last = e
        print(f"  {url} attempt {attempt + 1}: {last}", file=sys.stderr)
        time.sleep(5 * (attempt + 1))
    raise FetchError(f"{url}: {last}")


def cached(name: str, url: str, validate) -> bytes:
    """Fetch once into cache/customs_<name>, shape-checked BEFORE caching."""
    CACHE.mkdir(exist_ok=True)
    path = CACHE / f"customs_{name}"
    if path.exists():
        return path.read_bytes()
    body = get(url)
    validate(body)
    path.write_bytes(body)
    return body


def resolve_links() -> dict[str, str]:
    """{index label: absolute CSV url}, read from time.htm's anchors."""
    def ok(body: bytes) -> None:
        text = body.decode("cp932", errors="replace")
        check("d41ca.csv" in text and "d52ca" in text,
              "time.htm: the index no longer links the d41/d52 files")
    text = cached("time.htm", INDEX, ok).decode("cp932", errors="replace")
    links = {}
    for href, label in re.findall(
            r'<a[^>]*href="(data/d\d{2}[cm]a\d*\.csv)"[^>]*>([^<]+)</a>', text):
        links[html.unescape(label).strip()] = BASE + href
    return links


def csv_validator(title_token: str):
    def ok(body: bytes) -> None:
        text = body.decode("cp932", errors="strict")
        check(text.startswith("《") and title_token in text.splitlines()[0],
              f"not a Customs series file for {title_token!r}: "
              f"{text[:80]!r}")
        check("千円" in text, "the ¥1,000 unit marker is gone")
    return ok


def rows(body: bytes) -> list[list[str]]:
    """Data rows only: those whose first cell is a year or year/month."""
    out = []
    for line in body.decode("cp932").splitlines():
        cells = [c.strip() for c in line.split(",")]
        if cells and re.fullmatch(r"\d{4}(/\d{2})?", cells[0]):
            out.append(cells)
    return out


def num(cell: str) -> int | None:
    """'-' marks a suppressed or nil cell: a hole, never a zero."""
    if cell in ("", "-"):
        return None
    check(cell.isdigit(), f"unexpected cell {cell!r}")
    return int(cell)


def world(links: dict[str, str]) -> tuple[dict[int, tuple[int, int]],
                                           int, int, tuple[int, int]]:
    """Annual totals, plus (running year, real months, YTD totals)."""
    for label in (WORLD_ANNUAL, WORLD_MONTHLY):
        check(label in links, f"time.htm: no link labelled {label!r}")
    annual_rows = rows(cached("d41ca.csv", links[WORLD_ANNUAL],
                              csv_validator("世界")))
    annual = {}
    for cells in annual_rows:
        x, m = num(cells[1]), num(cells[2])
        check(x is not None and m is not None and x > 0 and m > 0,
              f"d41ca {cells[0]}: a zero or blank in the annual file")
        annual[int(cells[0])] = (x, m)

    monthly: dict[int, list[tuple[int, int, int]]] = {}
    for cells in rows(cached("d41ma.csv", links[WORLD_MONTHLY],
                             csv_validator("世界"))):
        y, mo = map(int, cells[0].split("/"))
        monthly.setdefault(y, []).append((mo, num(cells[1]) or 0,
                                          num(cells[2]) or 0))
    running = max(monthly)
    check(running == max(annual) + 1,
          f"monthly file runs to {running}, annual to {max(annual)}: "
          "the running year is not the one after the last annual row")
    months = sorted(monthly[running])
    real = [(mo, x, m) for mo, x, m in months if x > 0 and m > 0]
    # Zeros must be a trailing block: months 1..n real, n+1..12 zero-filled.
    check([mo for mo, _, _ in real] == list(range(1, len(real) + 1)),
          f"{running}: a zero month sits inside the published run")
    check(all(x == 0 and m == 0 for mo, x, m in months if mo > len(real)),
          f"{running}: a half-zero month after the published run")
    check(1 <= len(real) <= 12, f"{running}: {len(real)} real months")
    ytd = (sum(x for _, x, _ in real), sum(m for _, _, m in real))

    # The monthly rows of a finished year must add up to its annual row
    # (the annual file is the confirmed figure; allow 0.5% for revisions).
    for y in (2006, 2024, LAST_FULL_YEAR):
        mx = sum(x for _, x, _ in monthly[y])
        check(abs(mx - annual[y][0]) / annual[y][0] < 0.005,
              f"{y}: monthly exports sum {mx} vs annual {annual[y][0]}")
    return annual, running, len(real), ytd


def partners(links: dict[str, str]) -> dict[tuple[str, str], dict[int, int | None]]:
    out = {}
    for key, x_label, m_label in PARTNERS:
        for flow, label in (("x", x_label), ("m", m_label)):
            check(label in links, f"time.htm: no link labelled {label!r}")
            url = links[label]
            name = url.rsplit("/", 1)[-1]
            check(re.fullmatch(r"d[56]2ca\d{3}\.csv", name) is not None
                  and name[1] == ("5" if flow == "x" else "6"),
                  f"{label!r} links to {name}, not a d52/d62 annual file")
            body = cached(name, url, csv_validator(label.split()[0]))
            text = body.decode("cp932")
            check(("輸出" if flow == "x" else "輸入") in text.splitlines()[0],
                  f"{name}: title is not the {flow} direction")
            header = next(line for line in text.splitlines()
                          if line.startswith("報道発表品目名"))
            check(header.split(",")[1].strip() == "総額",
                  f"{name}: column 1 is no longer 総額")
            out[(key, flow)] = {int(c[0]): num(c[1]) for c in rows(body)}
    return out


def wb(code: str) -> dict[int, float]:
    def ok(body: bytes) -> None:
        p = json.loads(body)
        check(isinstance(p, list) and len(p) > 1 and isinstance(p[1], list),
              f"WB {code}: not an indicator response")
    p = json.loads(cached(f"wb_{code}.json", WB.format(code=code), ok))
    return {int(r["date"]): float(r["value"]) for r in p[1]
            if r.get("value") is not None}


def cross_check(annual: dict[int, tuple[int, int]]) -> None:
    """Customs 2024 exports in US$ vs the World Bank / WTO merchandise
    exports figure — a second publisher on the same quantity."""
    fx = wb("PA.NUS.FCRF")[2024]
    wto = wb("TX.VAL.MRCH.CD.WT")[2024]
    usd = annual[2024][0] * 1_000 / fx
    gap = usd / wto - 1
    print(f"  cross-check 2024 exports: customs ¥{annual[2024][0] / 1e9:,.2f}tn"
          f" ÷ {fx:.2f} = US${usd / 1e9:,.1f}bn vs WB/WTO "
          f"US${wto / 1e9:,.1f}bn ({gap:+.2%})")
    check(abs(gap) < 0.02, f"2024 exports disagree with WB by {gap:+.2%}")


def bn(v: int | None) -> str:
    """¥1,000 → ¥ billion, one decimal; a hole stays blank."""
    return "" if v is None else f"{v / 1_000_000:.1f}"


def main() -> None:
    print("Japan Customs trade totals")
    links = resolve_links()
    annual, running, months, ytd = world(links)
    for y, (x, m) in MUST_MATCH_WORLD.items():
        check(annual.get(y) == (x, m), f"d41ca {y}: {annual.get(y)} != {(x, m)}")
    cross_check(annual)
    print(f"  {running}: {months} of 12 months published "
          f"(the rest are zero-filled and dropped)")

    DATA.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Japan Customs, 普通貿易統計 d41ca (annual) / d41ma (monthly, running year only).",
        "# Goods only, customs basis: exports FOB, imports CIF. NOT the BoP goods account.",
        "# Units: ¥ BILLION, converted from the published ¥ thousand (千円) ÷ 1,000,000.",
        "# Calendar years. months = months of data behind the row. The running year is",
        f"# written ONLY as a year-to-date ({running}: {months} of 12 months; the later",
        "# months are zero-filled in the source and are not data) in the *_ytd columns;",
        "# its annual columns stay blank.",
        "year,exports_jpy_bn,imports_jpy_bn,balance_jpy_bn,months,"
        "exports_ytd_jpy_bn,imports_ytd_jpy_bn,balance_ytd_jpy_bn",
    ]
    for y in range(YEAR_FROM, running + 1):
        if y in annual:
            x, m = annual[y]
            lines.append(f"{y},{bn(x)},{bn(m)},{bn(x - m)},12,,,")
        elif y == running:
            x, m = ytd
            lines.append(f"{y},,,,{months},{bn(x)},{bn(m)},{bn(x - m)}")
        else:
            lines.append(f"{y},,,,,,,")
    (DATA / "trade_from_customs.csv").write_text("\n".join(lines) + "\n")
    print(f"  data/trade/trade_from_customs.csv  {sum(not l.startswith('#') for l in lines) - 1} rows "
          f"({YEAR_FROM}–{running})")

    series = partners(links)
    for (key, flow, y), want in MUST_MATCH_PARTNER.items():
        got = series[(key, flow)].get(y)
        check(got is not None and abs(got / 1e9 - want) < 0.01,
              f"{key} {flow} {y}: {got} vs ¥{want}tn")
    last = max(max(s) for s in series.values())
    check(last == LAST_FULL_YEAR, f"partner files end {last}")
    cols = [f"{flow}_{key}_jpy_bn" for key, _, _ in PARTNERS
            for flow in ("exports", "imports")]
    lines = [
        "# Japan Customs, d52caNNN (exports to) / d62caNNN (imports from), column 総額.",
        "# Units: ¥ BILLION, converted from ¥ thousand (千円) ÷ 1,000,000. Calendar years;",
        "# full years only (the running year is not in the annual partner files).",
        "# BREAK: the EU line is the membership OF THE TIME, not today's — 2019 exports",
        "# ¥8,955.3bn is EU28 (UK included, = the 2019 press release); 2020 on is EU27,",
        "# so 2019→2020 is a definitional drop plus COVID, not a fall to read. The other",
        "# aggregates (Asia, ASEAN, Middle East) carry no composition note in the files.",
        "# Blank = '-' in the source (nil/suppressed).",
        "year," + ",".join(cols),
    ]
    for y in range(YEAR_FROM, last + 1):
        cells = []
        for key, _, _ in PARTNERS:
            for flow in ("x", "m"):
                cells.append(bn(series[(key, flow)].get(y)))
        lines.append(f"{y}," + ",".join(cells))
    (DATA / "trade_partners_from_customs.csv").write_text("\n".join(lines) + "\n")
    print(f"  data/trade/trade_partners_from_customs.csv  {sum(not l.startswith('#') for l in lines) - 1} rows "
          f"({YEAR_FROM}–{last}, {len(PARTNERS)} partners × 2)")
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    try:
        main()
    except FetchError as e:
        sys.exit(f"FAILED: {e}")
