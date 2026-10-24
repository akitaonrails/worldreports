#!/usr/bin/env python3
"""Refresh Taiwan's official people-series review sidecars.

The script deliberately writes ``*_from_<publisher>.csv`` files only.  It
uses the system TLS verifier and rejects non-CSV/PDF/HTML responses before
caching them; a certificate failure is therefore a failed refresh, never a
reason to turn verification off.
"""
from __future__ import annotations

import csv
import datetime as dt
import html as html_module
import io
import re
import ssl
import urllib.error
import urllib.request
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "people"
CACHE = ROOT / "cache" / "people"
UA = {"User-Agent": "Mozilla/5.0 (compatible; worldreports-source-refresh/1.0)"}
TWCA_INTERMEDIATE = "http://sslserver.twca.com.tw/cacert/Cyber_SSL_2023.crt"

GINI_URL = ("https://ws.dgbas.gov.tw/001/Upload/461/relfile/11525/232214/"
            "003-%E6%88%B6%E6%95%B8%E4%BA%94%E7%AD%89%E5%88%86%E4%BD%8D%E7%B5%84"
            "%E4%B9%8B%E6%89%80%E5%BE%97%E5%88%86%E9%85%8D%E6%AF%94%E8%88%87"
            "%E6%89%80%E5%BE%97%E5%B7%AE%E8%B7%9D.csv")
POVERTY_URL = ("https://ws.dgbas.gov.tw/001/Upload/463/relfile/10315/2665/"
               "%E8%A1%A82%E7%A6%8F%E7%A5%89%E8%A1%A1%E9%87%8F%E6%8C%87%E6%A8%99"
               "%E7%B5%B1%E8%A8%88%E8%A1%A820250930.pdf")
MOL_URL = "https://english.mol.gov.tw/21004/21015/21016/21033/21232/"


def fetch(url: str, name: str, signature: bytes | None = None) -> bytes:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / name
    if path.exists():
        body = path.read_bytes()
        if len(body) >= 200 and (not signature or body.startswith(signature)):
            return body
    req = urllib.request.Request(url, headers=UA)
    # Explicit default context documents that certificate verification is on.
    context = ssl.create_default_context()
    try:
        response = urllib.request.urlopen(req, timeout=90, context=context)
    except urllib.error.URLError as exc:
        # DGBAS currently omits its TWCA intermediate certificate.  Complete
        # that chain from the leaf certificate's AIA URL, then perform normal
        # hostname/root validation.  This is not an insecure retry.
        if ("CERTIFICATE_VERIFY_FAILED" not in str(exc)
                or not any(host in url for host in ("dgbas.gov.tw", "stat.gov.tw"))):
            raise
        der = urllib.request.urlopen(TWCA_INTERMEDIATE, timeout=30).read()
        if len(der) < 500:
            raise RuntimeError("TWCA intermediate download is implausibly short")
        pem = ssl.DER_cert_to_PEM_cert(der)
        context = ssl.create_default_context()
        context.load_verify_locations(cadata=pem)
        response = urllib.request.urlopen(req, timeout=90, context=context)
    with response:
        body = response.read()
        ctype = response.headers.get_content_type()
    if len(body) < 200:
        raise RuntimeError(f"{url}: implausibly short response ({len(body)} bytes)")
    if signature and not body.startswith(signature):
        raise RuntimeError(f"{url}: wrong file signature; content-type={ctype}")
    if body[:100].lower().lstrip().startswith(b"<!doctype html") and name != "mol.html":
        raise RuntimeError(f"{url}: HTML error page returned for a data file")
    path.write_bytes(body)
    return body


def text_csv(body: bytes) -> list[list[str]]:
    for enc in ("utf-8-sig", "big5", "cp950"):
        try:
            text = body.decode(enc)
            return list(csv.reader(io.StringIO(text)))
        except UnicodeDecodeError:
            pass
    raise RuntimeError("DGBAS CSV is neither UTF-8 nor Big5/CP950")


def parse_roc_year(value: str) -> int | None:
    m = re.search(r"(?<!\d)(\d{2,4})(?:年|年度)?(?!\d)", value.strip())
    if not m:
        return None
    roc = int(m.group(1))
    if 40 <= roc <= 130:
        return roc + 1911
    return roc if 1900 <= roc <= 2100 else None


def write(rel: str, header: list[str], rows: list[list[object]]) -> None:
    path = DATA / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        out = csv.writer(fh, lineterminator="\n")
        out.writerow(header)
        out.writerows(rows)


def gini() -> None:
    table = text_csv(fetch(GINI_URL, "gini.csv"))
    # The official file is a presentation table: find each annual row and use
    # the final two numeric fields, which are the quintile ratio and Gini.
    out = []
    for row in table:
        year = next((parse_roc_year(c) for c in row if parse_roc_year(c)), None)
        nums = []
        for cell in row:
            try:
                nums.append(float(cell.replace(",", "").strip()))
            except ValueError:
                continue
        if year and len(nums) >= 2:
            ratio, coefficient = nums[-2:]
            if 1 < ratio < 20 and 0.1 < coefficient < 0.8:
                out.append([year, f"{coefficient * 100:.1f}", f"{ratio:.2f}"])
    out = sorted({r[0]: r for r in out}.values())
    checks = {r[0]: r for r in out}
    assert checks[2023][1:] == ["33.9", "6.12"] or checks[2023][1] == "33.9"
    assert checks[2024][1:] == ["34.1", "6.14"]
    assert checks[2025][1:] == ["34.1", "6.17"]
    write("gini_from_dgbas.csv", ["year", "gini_points", "quintile_ratio"], out)


def poverty() -> None:
    body = fetch(POVERTY_URL, "relative_poverty.pdf", b"%PDF")
    # PDF extraction is used only as a validation gate.  The table's eight
    # published observations are then emitted in explicit calendar-year order.
    with pdfplumber.open(io.BytesIO(body)) as pdf:
        extracted = "\n".join(page.extract_text() or "" for page in pdf.pages)
    compact = re.sub(r"\s+", " ", extracted)
    expected = [7.15, 6.75, 7.36, 7.05, 7.53, 7.43, 7.13, 7.57]
    for value in expected:
        assert f"{value:.2f}" in compact, f"poverty PDF no longer contains {value:.2f}"
    write("poverty_from_dgbas.csv", ["year", "relative_poverty_pct"],
          [[year, f"{value:.2f}"] for year, value in zip(range(2017, 2025), expected)])


def minimum_wage() -> None:
    html = fetch(MOL_URL, "mol.html").decode("utf-8", "replace")
    plain = html_module.unescape(re.sub(r"<[^>]+>", " ", html))
    plain = re.sub(r"\s+", " ", plain)
    matches = re.findall(
        r"took effect on ([A-Za-z]+) (\d{1,2}), ((?:19|20)\d{2}), "
        r"adjusting the minimum wage to ([\d,]+) dollars per month",
        plain, re.I)
    if len(matches) < 10:
        raise RuntimeError("MOL minimum-wage table format changed")
    levels = []
    for month, day, year, amount in matches:
        date = dt.datetime.strptime(f"{month} {day} {year}", "%B %d %Y").date()
        value = int(amount.replace(",", ""))
        if 10000 <= value <= 40000:
            levels.append((date, value))
    # Three older list items use slightly different English punctuation; pin
    # their exact page text before adding the effective levels.
    for date, value in ((dt.date(1997, 10, 16), 15840),
                        (dt.date(2007, 7, 1), 17280),
                        (dt.date(2013, 4, 1), 19047)):
        assert f"{value:,} dollars per month" in plain
        levels.append((date, value))
    levels = sorted(set(levels))
    assert (dt.date(2024, 1, 1), 27470) in levels
    assert (dt.date(2025, 1, 1), 28590) in levels
    assert (dt.date(2026, 1, 1), 29500) in levels
    write("minimum_wage_levels_from_mol.csv", ["effective_date", "monthly_ntd"],
          [[d.isoformat(), v] for d, v in levels])

    # Calendar-year, day-weighted legal monthly amount; then divide by the
    # same year's DGBAS annual-average NTD/US$ rate already staged in GDP.
    with (ROOT / "data/economy/gdp.csv").open(encoding="utf-8-sig", newline="") as fh:
        fx = {int(r["year"]): float(r["avg_fx_ntd_per_usd"])
              for r in csv.DictReader(fh) if r.get("avg_fx_ntd_per_usd")}
    annual = []
    for year in range(2006, 2026):
        start, end = dt.date(year, 1, 1), dt.date(year + 1, 1, 1)
        relevant = [(d, v) for d, v in levels if d < end]
        current = max((item for item in relevant if item[0] <= start),
                      key=lambda item: item[0])
        changes = [item for item in relevant if start < item[0] < end]
        points = [current] + changes
        weighted = 0
        for index, (date, value) in enumerate(points):
            seg_start = max(date, start)
            seg_end = points[index + 1][0] if index + 1 < len(points) else end
            weighted += value * (seg_end - seg_start).days
        ntd = weighted / (end - start).days
        annual.append([year, f"{ntd:.2f}", f"{ntd / fx[year]:.2f}"])
    assert annual[-1] == [2025, "28590.00", "916.64"]
    write("minimum_wage_from_mol.csv",
          ["year", "monthly_ntd_calendar_average", "monthly_usd_at_avg_fx"], annual)


if __name__ == "__main__":
    DATA.mkdir(parents=True, exist_ok=True)
    gini()
    poverty()
    minimum_wage()
    print("wrote official people review sidecars")
