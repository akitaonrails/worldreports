#!/usr/bin/env python3
"""Refresh the Bank of Japan series into sidecar CSVs.

Usage:  python3 -I countries/japan/fetch/fetch_boj.py

Everything here comes from the Bank's Time-Series Data Search API
(https://www.stat-search.boj.or.jp/api/v1/getDataCode, manual at
/info/api_manual_en.pdf). It is anonymous — no key — and answers JSON:

  STATUS 200 + MESSAGEID M181000I    success; anything else is a failure
  RESULTSET[].VALUES.SURVEY_DATES    YYYYMM (monthly), YYYYQQ (quarterly,
                                     so 202504 is 2025 Q4), YYYY (annual)
  NEXTPOSITION                       non-null when a request was cut at
                                     250 series / 60,000 points: page on

Quirks found while writing this, all handled below:

  - The server GZIPS its error bodies (and sometimes its successes)
    whatever the request said, so every payload is decompressed on magic
    bytes before it is parsed.
  - Mixing frequencies in one request (a quarterly FF code with its annual
    twin) is a 400, M181014E "Frequency not matching"; requests are
    grouped by frequency.
  - Missing observations come back as null inside VALUES; they stay
    blank, never zero.

Series, by output file (all yen amounts are published in 100 MILLION yen,
億円, and converted here to ¥ BILLION by dividing by 10):

  markets/rates_from_boj.csv
    FM02 STRACLUCON   uncollateralised overnight call rate, monthly average
    IR01 MADR1M       basic discount rate / basic loan rate (monthly)
    FM01 STRDCLUCON   the same call rate, daily — used only to check that
                      its monthly mean reproduces FM02, never written
  markets/usdjpy_from_boj.csv
    FM08 FXERM07 (monthly average) / FXERM06 (end of month), yen per USD
  markets/reer_from_boj.csv
    FM09 FX180110001 nominal / FX180110002 real effective rate, CY2020=100
  markets/monetary_base_from_boj.csv
    MD01 MABS1AN11 monetary base / MABS1AN113 current-account balances,
    average amounts outstanding
  trade/current_account_from_boj.csv
    BP01 BPBP6JYNCB current account, with goods (TB), services (SN),
    primary income (PIN) and secondary income (SIN) net balances
  fiscal/gg_liabilities_from_boj.csv
    FF general government, quarterly stocks: debt securities (L300), loans
    (L200), total financial assets (A900) and the balancing item L700.
    THE TRAP: FOF_FFAS420L900, "Liabilities/Total/General government", is
    NOT the government's liabilities. A flow-of-funds liabilities column
    closes with L700 "Difference between financial assets and
    liabilities", so L900 equals total financial ASSETS (A900) to the
    yen — 2025 Q4: 9,486,308 both, while the liabilities proper are
    L900 − L700 = 13,992,259 (¥1,399tn). The discovery pass read L900 as
    the debt; this file writes liabilities as L900 − L700 and asserts
    L900 == A900 every quarter. The annual end-March twin FOF_FFYS420L900
    is asserted to equal the March quarter rather than written twice.
  credit/household_debt_from_boj.csv
    FF FOF_FFAS430L200 household loans, L241 housing loans, L242
    consumer credit (quarterly stocks)

NOT here, and pending: the policy-rate TARGET. The API has no series for
it, and the target changed kind three times inside the window (call-rate
target → monetary base Apr-2013 → −0.1% plus YCC → call-rate target
Mar-2024). The realised call rate is what rates_from_boj.csv carries.

Outputs are `_from_boj` sidecars. Nothing here overwrites a curated file.
"""
from __future__ import annotations

import csv
import gzip
import json
import statistics
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache"
API = "https://www.stat-search.boj.or.jp/api/v1/getDataCode"
UA = {"User-Agent": "worldreports data fetcher (python urllib)",
      "Accept-Encoding": "gzip"}
Y0, Y1 = 2006, 2026
OK = (200, "M181000I")

# (db, start, [codes]) — one request each; every code in a request shares
# a frequency, or the API answers 400.
REQUESTS = {
    "call_m": ("FM02", "200601", ["STRACLUCON"]),
    "call_d": ("FM01", "202501", ["STRDCLUCON"]),
    "loanrate": ("IR01", "200601", ["MADR1M"]),
    "usdjpy": ("FM08", "200601", ["FXERM07", "FXERM06"]),
    "eer": ("FM09", "200601", ["FX180110001", "FX180110002"]),
    "base": ("MD01", "200601", ["MABS1AN11", "MABS1AN113"]),
    "bop": ("BP01", "200601", ["BPBP6JYNCB", "BPBP6JYNTB", "BPBP6JYNSN",
                               "BPBP6JYNPIN", "BPBP6JYNSIN"]),
    "ff_q": ("FF", "200601", ["FOF_FFAS420L900", "FOF_FFAS420L700",
                              "FOF_FFAS420A900", "FOF_FFAS420L300",
                              "FOF_FFAS420L200", "FOF_FFAS430L200",
                              "FOF_FFAS430L241", "FOF_FFAS430L242"]),
    "ff_fy": ("FF", "2005", ["FOF_FFYS420L900"]),
}

# What each series' published name and unit must say before it is used:
# the code alone does not prove the Bank still means the same thing by it.
EXPECT = {
    "STRACLUCON": ("Call Rate, Uncollateralized Overnight/Average", "percent"),
    "STRDCLUCON": ("Call Rate, Uncollateralized Overnight", "percent"),
    "MADR1M": ("Basic Discount Rate and Basic Loan Rate", "percent"),
    "FXERM07": ("Average in the Month", "Yen per U.S. Dollar"),
    "FXERM06": ("End of Month", "Yen per U.S. Dollar"),
    "FX180110001": ("Nominal Effective Exchange Rate", "2020=100"),
    "FX180110002": ("Real Effective Exchange Rate", "2020=100"),
    "MABS1AN11": ("Monetary Base/Average Amounts Outstanding", "100 million yen"),
    "MABS1AN113": ("Current Account Balances", "100 million yen"),
    "BPBP6JYNCB": ("Current account/Net balance", "100 million yen"),
    "BPBP6JYNTB": ("Goods/Net balance", "100 million yen"),
    "BPBP6JYNSN": ("Services/Net balance", "100 million yen"),
    "BPBP6JYNPIN": ("Primary income/Net balance", "100 million yen"),
    "BPBP6JYNSIN": ("Secondary income", "100 million yen"),
    "FOF_FFAS420L900": ("Liabilities/Total/General government/Stock",
                        "100 million yen"),
    "FOF_FFYS420L900": ("Liabilities/Total/General government/Stock",
                        "100 million yen"),
    "FOF_FFAS420L700": ("Difference between financial assets and liabilities/"
                        "General government/Stock", "100 million yen"),
    "FOF_FFAS420A900": ("Assets/Total/General government/Stock", "100 million yen"),
    "FOF_FFAS420L300": ("Liabilities/Debt securities/General government/Stock",
                        "100 million yen"),
    "FOF_FFAS420L200": ("Liabilities/Loans/General government/Stock",
                        "100 million yen"),
    "FOF_FFAS430L200": ("Liabilities/Loans/Households/Stock", "100 million yen"),
    "FOF_FFAS430L241": ("Housing loans/Households/Stock", "100 million yen"),
    "FOF_FFAS430L242": ("Consumer credit/Households/Stock", "100 million yen"),
}


def _decode(blob: bytes) -> dict:
    if blob[:2] == b"\x1f\x8b":
        blob = gzip.decompress(blob)
    return json.loads(blob.decode("utf-8"))


def call(db: str, codes: list[str], start: str, position: int | None = None) -> dict:
    url = f"{API}?format=json&lang=en&db={db}&code={','.join(codes)}&startDate={start}"
    if position:
        url += f"&startPosition={position}"
    last = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=120) as r:
                return _decode(r.read())
        except urllib.error.HTTPError as e:
            body = e.read()
            try:
                info = _decode(body)
                last = f"HTTP {e.code} {info.get('MESSAGEID')} {info.get('MESSAGE')}"
            except Exception:  # noqa: BLE001
                last = f"HTTP {e.code}"
            if e.code in (400, 404):
                break                     # a bad request does not get better
            time.sleep(10 * (attempt + 1) if e.code in (403, 429) else 3 * (attempt + 1))
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"boj {db} {codes}: {last}")


def check(payload: dict, codes: list[str]) -> None:
    """The shape a usable answer must have, checked BEFORE it is cached."""
    if (payload.get("STATUS"), payload.get("MESSAGEID")) != OK:
        raise RuntimeError(f"boj: STATUS {payload.get('STATUS')} "
                           f"{payload.get('MESSAGEID')} {payload.get('MESSAGE')}")
    got = [r.get("SERIES_CODE") for r in payload.get("RESULTSET", [])]
    if sorted(got) != sorted(codes):
        raise RuntimeError(f"boj: asked for {codes}, got {got}")
    for r in payload["RESULTSET"]:
        v = r.get("VALUES") or {}
        dates, vals = v.get("SURVEY_DATES") or [], v.get("VALUES") or []
        if not dates or len(dates) != len(vals):
            raise RuntimeError(f"boj {r['SERIES_CODE']}: dates/values misaligned")
        name, unit = EXPECT[r["SERIES_CODE"]]
        if name.lower() not in r["NAME_OF_TIME_SERIES"].lower():
            raise RuntimeError(f"boj {r['SERIES_CODE']}: name is "
                               f"{r['NAME_OF_TIME_SERIES']!r}, expected {name!r}")
        if unit.lower() not in r["UNIT"].lower():
            raise RuntimeError(f"boj {r['SERIES_CODE']}: unit is {r['UNIT']!r}, "
                               f"expected {unit!r}")


def fetch(key: str) -> dict[str, list[tuple[int, float]]]:
    """{code: [(survey date as int, value)]} ascending, nulls dropped."""
    db, start, codes = REQUESTS[key]
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / f"boj_{key}_{db}.json"
    if cache_file.exists():
        pages = json.loads(cache_file.read_text())
    else:
        pages, position = [], None
        while True:
            payload = call(db, codes, start, position)
            check(payload, codes)
            pages.append(payload)
            position = payload.get("NEXTPOSITION")
            if not position:
                break
            time.sleep(1.5)
        cache_file.write_text(json.dumps(pages, ensure_ascii=False))
        time.sleep(1.5)                   # "excessive access may be restricted"
    out: dict[str, list[tuple[int, float]]] = defaultdict(list)
    for payload in pages:
        for r in payload["RESULTSET"]:
            v = r["VALUES"]
            for d, x in zip(v["SURVEY_DATES"], v["VALUES"]):
                if x is None or x == "":
                    continue              # a hole stays a hole
                out[r["SERIES_CODE"]].append((int(d), float(x)))
    for code in codes:
        if not out.get(code):
            raise RuntimeError(f"boj {code}: no observations")
        out[code].sort()
    return dict(out)


# --- reshaping ------------------------------------------------------------

def monthly(obs):
    """{year: {month: value}} from YYYYMM survey dates."""
    out: dict[int, dict[int, float]] = defaultdict(dict)
    for d, x in obs:
        out[d // 100][d % 100] = x
    return out


def quarterly(obs):
    """{year: {quarter: value}} from YYYYQQ survey dates (202504 = 2025 Q4)."""
    out: dict[int, dict[int, float]] = defaultdict(dict)
    for d, x in obs:
        q = d % 100
        if q not in (1, 2, 3, 4):
            raise RuntimeError(f"boj: {d} is not a YYYYQQ quarter")
        out[d // 100][q] = x
    return out


def running_year(*series) -> int:
    return max(max(s) for s in series)


def mean_of_year(m, year, running, nd):
    """The mean of a year's months; blank if a past year is incomplete.

    The running year is incomplete by definition: it is emitted with its
    month count beside it (and the plate says "2026: 9 of 12 months").
    """
    months = m.get(year, {})
    if not months or (len(months) < 12 and year < running):
        return ""
    return round(statistics.fmean(months.values()), nd)


def sum_of_year(m, year, nd=1, scale=0.1):
    """A full year's flow total, or blank — a part-year is not a small year."""
    months = m.get(year, {})
    if len(months) < 12:
        return ""
    return round(sum(months.values()) * scale, nd)


def december(m, year, nd):
    v = m.get(year, {}).get(12)
    return "" if v is None else round(v, nd)


def latest(m, year):
    months = m.get(year, {})
    return (max(months), months[max(months)]) if months else (None, None)


def bn(v):
    """100 million yen (億円) to ¥ billion, explicitly: divide by ten."""
    return "" if v in ("", None) else round(v / 10, 1)


def write(path: Path, comment: str, header: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        for line in comment.strip().splitlines():
            fh.write(f"# {line.strip()}\n")
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    print(f"  {path.relative_to(ROOT)}  {len(rows)} rows")


def expect(label, got, want, tol):
    if got in ("", None) or abs(float(got) - want) > tol:
        raise RuntimeError(f"spot check {label}: got {got!r}, expected {want} ± {tol}")
    print(f"    ok  {label} = {got}")


# --- main -----------------------------------------------------------------

def main() -> None:
    print("Bank of Japan (Time-Series Data Search API)")
    raw = {key: fetch(key) for key in REQUESTS}

    # Rates ------------------------------------------------------------
    call_m = monthly(raw["call_m"]["STRACLUCON"])
    loan = monthly(raw["loanrate"]["MADR1M"])
    run = running_year(call_m)

    # The daily twin must reproduce the monthly average it is built from.
    daily = defaultdict(list)
    for d, x in raw["call_d"]["STRDCLUCON"]:
        daily[d // 100].append(x)
    for ym in sorted(daily)[:-1][-3:]:        # last three complete months
        y, mo = divmod(ym, 100)
        mean = statistics.fmean(daily[ym])
        if abs(mean - call_m[y][mo]) > 0.002:
            raise RuntimeError(f"boj: FM01 daily mean {mean:.4f} for {ym} does "
                               f"not reproduce FM02 {call_m[y][mo]}")

    rows = []
    for year in range(Y0, Y1 + 1):
        m_last, _ = latest(call_m, year)
        _, loan_last = latest(loan, year)
        loan_v = december(loan, year, 3) if year < run else (
            "" if loan_last is None else round(loan_last, 3))
        rows.append([year, mean_of_year(call_m, year, run, 3),
                     december(call_m, year, 3), loan_v,
                     len(call_m.get(year, {})),
                     f"{year}-{m_last:02d}" if m_last else ""])
    write(DATA / "markets" / "rates_from_boj.csv", """
        Bank of Japan, uncollateralised overnight call rate (FM02 STRACLUCON, monthly average, % p.a.)
        and the basic discount/loan rate (IR01 MADR1M, % p.a.). Calendar years.
        call_rate_avg is the mean of the year's monthly averages; call_rate_dec is the December monthly average.
        This is the REALISED market rate, not the policy target: the target changed kind three times in the window
        (call-rate target; monetary base Apr-2013 to Sep-2016; -0.1% on policy-rate balances plus YCC Jan-2016 to Mar-2024;
        call-rate target again) and is hand-curated elsewhere (SOURCES.yaml meta.pending).
        basic_loan_rate is the December value, and for the running year the latest month (see asof_month).
        The running year is partial: months says how many months it covers.
    """, ["year", "call_rate_avg", "call_rate_dec", "basic_loan_rate",
          "months", "asof_month"], rows)
    print("    spot checks:")
    expect("call rate Dec-2016", call_m[2016][12], -0.044, 0.0005)
    expect("call rate Aug-2024", call_m[2024][8], 0.227, 0.0005)
    expect("call rate Dec-2025", call_m[2025][12], 0.557, 0.0005)
    expect("call rate Sep-2026", call_m[2026][9], 1.043, 0.0005)

    # USD/JPY -----------------------------------------------------------
    fx_avg = monthly(raw["usdjpy"]["FXERM07"])
    fx_eom = monthly(raw["usdjpy"]["FXERM06"])
    run = running_year(fx_avg)
    rows = []
    for year in range(Y0, Y1 + 1):
        m_last, _ = latest(fx_avg, year)
        rows.append([year, mean_of_year(fx_avg, year, run, 2),
                     december(fx_eom, year, 2), len(fx_avg.get(year, {})),
                     f"{year}-{m_last:02d}" if m_last else ""])
    write(DATA / "markets" / "usdjpy_from_boj.csv", """
        Bank of Japan, US dollar/yen spot rate at 17:00 JST, Tokyo market (FM08 FXERM07 monthly average,
        FXERM06 end of month). YEN PER US DOLLAR: a RISING line is a WEAKER yen.
        usdjpy_avg is the mean of the year's monthly averages; usdjpy_eoy is the end-December rate.
        The running year is partial: months says how many months it covers.
    """, ["year", "usdjpy_avg", "usdjpy_eoy", "months", "asof_month"], rows)
    print("    spot checks:")
    for y, want in ((2006, 116.28), (2011, 79.78), (2012, 79.79), (2015, 121.02),
                    (2022, 131.37), (2024, 151.50), (2025, 149.65)):
        expect(f"USD/JPY {y} mean", rows[y - Y0][1], want, 0.006)
    expect("USD/JPY Sep-2026", fx_avg[2026][9], 156.23, 0.005)

    # Effective exchange rates ------------------------------------------
    neer = monthly(raw["eer"]["FX180110001"])
    reer = monthly(raw["eer"]["FX180110002"])
    run = running_year(reer)
    rows = []
    for year in range(Y0, Y1 + 1):
        m_last, _ = latest(reer, year)
        rows.append([year, mean_of_year(neer, year, run, 2),
                     mean_of_year(reer, year, run, 2), len(reer.get(year, {})),
                     f"{year}-{m_last:02d}" if m_last else ""])
    write(DATA / "markets" / "reer_from_boj.csv", """
        Bank of Japan, effective exchange rates of the yen (FM09 FX180110001 nominal, FX180110002 real), CY2020=100,
        annual means of monthly values. HIGHER = STRONGER yen (the opposite direction from usdjpy).
        The pre-2010 broad series (FXCP7JP/FXCP8JP, March 1973=100) is discontinued and on another base; it is not spliced here.
        The running year is partial: months says how many months it covers.
    """, ["year", "neer_avg", "reer_avg", "months", "asof_month"], rows)
    if not 40 < rows[-1][2] < 120:
        raise RuntimeError(f"boj: REER {rows[-1]} outside any plausible range")

    # Monetary base -------------------------------------------------------
    mb = monthly(raw["base"]["MABS1AN11"])
    cab = monthly(raw["base"]["MABS1AN113"])
    run = running_year(mb)
    rows = []
    for year in range(Y0, Y1 + 1):
        m_last, v_last = latest(mb, year)
        if year < run:
            mb_v, cab_v = december(mb, year, 0), december(cab, year, 0)
        else:
            mb_v, cab_v = v_last, cab.get(year, {}).get(m_last)
        rows.append([year, bn(mb_v), bn(cab_v),
                     f"{year}-{(12 if year < run else m_last):02d}" if m_last else ""])
    write(DATA / "markets" / "monetary_base_from_boj.csv", """
        Bank of Japan, monetary base and its current-account-balances component (MD01 MABS1AN11, MABS1AN113),
        average amounts outstanding in the month. Published in 100 million yen; converted here to YEN BILLION (divided by 10).
        Each year is its December reading; the running year is its latest month (asof_month). Stocks, never summed.
        The monetary base WAS the operating target April 2013 - September 2016 (QQE): annotate the regime; it is not a policy rate.
    """, ["year", "monetary_base_bn", "current_account_balances_bn", "asof_month"], rows)

    # Current account -----------------------------------------------------
    bop = {c: monthly(raw["bop"][c]) for c in REQUESTS["bop"][2]}
    ca = bop["BPBP6JYNCB"]
    run = running_year(ca)
    rows = []
    for year in range(Y0, Y1 + 1):
        total = sum_of_year(ca, year)
        parts = [sum_of_year(bop[c], year) for c in
                 ("BPBP6JYNTB", "BPBP6JYNSN", "BPBP6JYNPIN", "BPBP6JYNSIN")]
        if total != "" and all(p != "" for p in parts) and abs(sum(parts) - total) > 1.0:
            raise RuntimeError(f"boj: {year} BoP components {parts} do not add to {total}")
        rows.append([year, total, *parts, len(ca.get(year, {}))])
    write(DATA / "trade" / "current_account_from_boj.csv", """
        Bank of Japan / Ministry of Finance, Balance of Payments (BPM6), BP01, monthly net balances summed to calendar years.
        Published in 100 million yen; converted here to YEN BILLION (divided by 10).
        current_account = goods + services + primary_income + secondary_income (checked to within ¥1bn of rounding).
        Annual totals only for complete years: a part-year is blank, with months saying how many months exist.
        BoP basis (goods on change of ownership, services included); NOT the customs-basis trade series, and never spliced with it.
    """, ["year", "current_account_bn", "goods_bn", "services_bn",
          "primary_income_bn", "secondary_income_bn", "months"], rows)
    print("    spot checks:")
    expect("current account CY2024 (¥bn)", rows[2024 - Y0][1], 29280, 10)
    expect("current account CY2025 (¥bn)", rows[2025 - Y0][1], 32240, 10)

    # Flow of funds: general government ---------------------------------
    ffq = {c: quarterly(raw["ff_q"][c]) for c in REQUESTS["ff_q"][2]}
    tot, diff, assets = (ffq["FOF_FFAS420L900"], ffq["FOF_FFAS420L700"],
                         ffq["FOF_FFAS420A900"])
    liab = defaultdict(dict)
    for y, qs in tot.items():
        for q, v in qs.items():
            a = assets.get(y, {}).get(q)
            if a is None or abs(a - v) > 0.5:
                raise RuntimeError(f"boj: FF GG L900 {v} != A900 {a} at {y}Q{q}: the "
                                   "liabilities column no longer closes on assets")
            d = diff.get(y, {}).get(q)
            if d is not None:
                liab[y][q] = v - d            # the instruments, without the balancing item
    gg_fy = dict(raw["ff_fy"]["FOF_FFYS420L900"])
    for fy, v in gg_fy.items():               # FY t ends March t+1 = Q1 of t+1
        q1 = tot.get(fy + 1, {}).get(1)
        if q1 is not None and abs(q1 - v) > 0.5:
            raise RuntimeError(f"boj: FFYS FY{fy} {v} != FFAS {fy + 1}Q1 {q1}")
    sec, loans = ffq["FOF_FFAS420L300"], ffq["FOF_FFAS420L200"]
    for y, qs in liab.items():
        for q, v in qs.items():
            core = sec.get(y, {}).get(q, 0) + loans.get(y, {}).get(q, 0)
            if not core <= v + 0.5:
                raise RuntimeError(f"boj: GG securities+loans {core} exceed liabilities {v}")
    write_ff(DATA / "fiscal" / "gg_liabilities_from_boj.csv", """
        Bank of Japan, Flow of Funds (2008 SNA), general government, stocks at quarter-end.
        gg_liabilities = all liability instruments = FOF_FFAS420L900 minus FOF_FFAS420L700. L900 ("Liabilities/Total") is NOT
        the debt: it closes on L700, the difference between financial assets and liabilities, and equals total financial
        assets (A900, written here as gg_financial_assets). net_financial_position is L700 (negative = net debtor).
        debt_securities (L300) and loans (L200) are PARTS of gg_liabilities. Published in 100 million yen; converted here to
        YEN BILLION (divided by 10). Each year is its December (Q4) stock; the running year is its latest quarter (asof_quarter).
        Securities are at MARKET value and general government is consolidated as the flow of funds defines it, so this is a
        different object from the MOF central-government face-value debt (central_debt_from_mof.csv) and the IMF gross
        general-government debt. Three debts, three files: none is spliced onto another.
    """, ["gg_liabilities_bn", "debt_securities_bn", "loans_bn",
          "gg_financial_assets_bn", "net_financial_position_bn"],
        [liab, sec, loans, assets, diff])
    print("    spot checks:")
    expect("FF GG L900 (= assets) 2025Q4 (¥100mn)", tot[2025][4], 9486308, 0.5)
    expect("FF GG liabilities L900-L700 2025Q4 (¥100mn)", liab[2025][4], 13992259, 0.5)

    # Flow of funds: households ------------------------------------------
    hh = [quarterly(raw["ff_q"][c]) for c in
          ("FOF_FFAS430L200", "FOF_FFAS430L241", "FOF_FFAS430L242")]
    write_ff(DATA / "credit" / "household_debt_from_boj.csv", """
        Bank of Japan, Flow of Funds (2008 SNA), households, liabilities, stocks: loans (FOF_FFAS430L200),
        of which housing loans (L241) and consumer credit (L242). Housing and consumer credit are PARTS of loans, not additions.
        Published in 100 million yen; converted here to YEN BILLION (divided by 10).
        Each year is its December (Q4) quarter-end stock; the running year is its latest quarter (asof_quarter). Stocks, never summed.
        A debt-to-income ratio needs ESRI household disposable income (fiscal-year flow): different period conventions, say so.
    """, ["household_loans_bn", "housing_loans_bn", "consumer_credit_bn"], hh)
    print("    spot checks:")
    expect("FF household loans 2025Q4 (¥100mn)", hh[0][2025][4], 3884339, 0.5)
    expect("FF household housing loans 2025Q4 (¥100mn)", hh[1][2025][4], 2209066, 0.5)
    expect("FF household loans 2006Q4 (¥100mn)", hh[0][2006][4], 3147719, 0.5)


def write_ff(path, comment, names, series):
    run = running_year(series[0])
    rows = []
    for year in range(Y0, Y1 + 1):
        qs = series[0].get(year, {})
        if not qs:
            continue
        q = 4 if year < run else max(qs)
        if year < run and 4 not in qs:
            rows.append([year, *([""] * len(names)), ""])
            continue
        rows.append([year, *[bn(s.get(year, {}).get(q, "")) for s in series],
                     f"{year}Q{q}"])
    write(path, comment, ["year", *names, "asof_quarter"], rows)


if __name__ == "__main__":
    main()
