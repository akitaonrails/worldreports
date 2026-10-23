#!/usr/bin/env python3
"""Refresh the Swiss National Bank series into sidecar CSVs.

Usage:  python3 -I countries/switzerland/fetch/fetch_snb.py

Everything comes from the SNB data portal's cube API,
https://data.snb.ch/api/cube/{id}/data/csv/en, keyless. The CSV is
semicolon-separated and quoted, carries a UTF-8 BOM and opens with a
two-line block (CubeId, PublishingDate), a blank line, then
Date;D0;…;Value. A series that has no observation in a period answers an
EMPTY Value (a trailing ';'), which stays blank here, never zero.

Things this source will mislead you about.

**Some cubes stop without saying so.** `rendoblim` (and `rendoblid`,
`rendopar`) froze at 2025-07 while still answering HTTP 200 with a fresh
header. The 10-year yield therefore comes from `rendeiduebm`, and every
monthly cube is asserted to reach a month close to today; `rendoblim` is
read once only to prove it agrees with `rendeiduebm` where both exist.

**The policy instrument changed in June 2019.** Until 2019-05 the SNB set
a target range for 3-month CHF Libor (lower and upper limit); from
2019-06 it sets the SNB policy rate. Three columns, never one line.

**Two household-debt definitions.** `bakredsekbrm` is loans by BANKS in
Switzerland to private households (monthly stocks from 1985); the
financial accounts (`frsekgevehup`, `frsekphupooe`) count loans from ALL
lenders (banks, insurers, pension funds) and run from 1999. They sit
about CHF 100bn apart and are two files. The bank series steps up by
CHF 60bn between 2006-08 and 2006-09, a reporting change visible in the
monthly stocks; every December row of the window is after it.

**The API answers a short default window.** Asked without `fromDate`, a
cube returns only its recent past (ten years for annual cubes, about 15
months for some monthly ones). That is why the balance of payments
(`bopcurra`, really from 1983), the household financial accounts
(`frsekgevehup`, from 1999) and the offered mortgage rates (`zikrepro`,
from 1990) once looked as if they began in 2016 or 2025-08. Every query
here names its `fromDate`, and every series' first period is asserted.

**Gold in the current account.** Foreign trade "Total 1" excludes
non-monetary gold (and other precious metals, gems, art); the foreign
trade total includes it. They are separate columns.

**Exchange rates are CHF per unit of foreign currency.** A rising line is
a WEAKER franc.

Scope: the Swiss currency area includes Liechtenstein, but whether each
cube's reporting population or counterparties include Liechtenstein is NOT
confirmed from the SNB's notes (open; see SOURCES.yaml meta.pending). The
sidecars say so rather than claim a scope.

Spot values recorded in DISCOVERY.md / SOURCES.yaml are asserted before
anything is written; the reserves and the current account are also
checked against the World Bank (a second publisher). Outputs are
`_from_snb.csv` sidecars; nothing here overwrites a curated file.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
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
BASE = "https://data.snb.ch/api/cube/{cube}/data/csv/en"
WB = ("https://api.worldbank.org/v2/country/CHE/indicator/{code}"
      "?format=json&per_page=200&date=2006:2026")
ESTAT = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
         "nasa_10_f_bs?geo=CH&sector=S14_S15&na_item=F4&finpos=LIAB"
         "&unit=MIO_NAC&co_nco=NCO&freq=A")
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
Y0, Y1 = 2006, 2026

# A monthly cube whose last month is older than this is treated as frozen.
MAX_STALE_MONTHS = 4

QUERIES = {
    "snboffzisa": "dimSel=D0(LZ,UG0,OG0)&fromDate=2006-01",
    "devkua": "dimSel=D1(EUR1,USD1)&fromDate=2006",
    "devkum": "dimSel=D0(M0,M1),D1(EUR1,USD1)&fromDate=2006-01",
    "rendeiduebm": "dimSel=D0(CHF),D1(2J,10J)&fromDate=2006-01",
    "rendoblim": "dimSel=D0(10J)&fromDate=2006-01",
    "zikreddet": "dimSel=D0(K,OBB,MBB,FH,FI)&fromDate=2009-01",
    "zikrepro": "dimSel=D0(M),D1(MV,20,50,10,31,SARJ03)&fromDate=1990-01",
    "bakredsekbrm": "dimSel=D1(T0,H,T2),D3(AA)&fromDate=2005-12",
    "frsekgevehup": "dimSel=D1(T5,HYP,KON,UKR)&fromDate=2006",
    "frsekphupooe": "dimSel=D0(BES),D1(T5),D2(T6),D3(T7,PH,POoE)&fromDate=2006",
    "snbimfra": "dimSel=D0(T1,T7)&fromDate=2006-01",
    "bopcurra": "dimSel=D0(L0,T0,T1,DAT1,DGZ,T3,T4,T7,T9),D1(E,A,S)&fromDate=2006",
}


# ---------------------------------------------------------------- fetch

def _get(url: str, timeout: int = 120) -> bytes:
    """GET with polite retries; 429/403 back off much longer."""
    last = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            last = e
            wait = 30 * (attempt + 1) if e.code in (403, 429) else 3 * (attempt + 1)
        except Exception as e:  # noqa: BLE001
            last = e
            wait = 3 * (attempt + 1)
        time.sleep(wait)
    raise RuntimeError(f"{url}: {last}")


def cube(name: str) -> tuple[str, list[dict]]:
    """One cube as (publishing date, [row dicts]); shape-checked, then cached."""
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / f"snb_{name}.csv"
    if cache_file.exists():
        text = cache_file.read_text(encoding="utf-8")
    else:
        url = BASE.format(cube=name) + "?" + QUERIES[name]
        text = _get(url).decode("utf-8-sig")
        lines = text.splitlines()
        # The shape it must have: CubeId line naming THIS cube, a
        # PublishingDate line, and a Date header. An HTML error page or a
        # JSON error object fails here and is never cached.
        if (len(lines) < 5 or lines[0].replace('"', "") != f"CubeId;{name}"
                or not lines[1].startswith('"PublishingDate"')
                or not lines[3].startswith('"Date"')):
            raise RuntimeError(f"snb {name}: unexpected payload {text[:200]!r}")
        cache_file.write_text(text, encoding="utf-8")
        time.sleep(1.5)
    lines = text.splitlines()
    published = lines[1].replace('"', "").split(";")[1]
    rows = list(csv.DictReader(io.StringIO("\n".join(lines[3:])), delimiter=";"))
    if not rows:
        raise RuntimeError(f"snb {name}: no data rows")
    return published, rows


def series(rows: list[dict], **dims) -> dict[str, float]:
    """{period: value} for one dimension combination; blanks dropped."""
    out: dict[str, float] = {}
    for r in rows:
        if all(r.get(k) == v for k, v in dims.items()):
            if r["Value"] in ("", None):
                continue
            if r["Date"] in out:
                raise RuntimeError(f"duplicate period {r['Date']} for {dims}")
            out[r["Date"]] = float(r["Value"])
    return out


def wb(code: str) -> dict[int, float]:
    cache_file = CACHE / f"snb_wb_{code}.json"
    if cache_file.exists():
        payload = json.loads(cache_file.read_text())
    else:
        payload = json.loads(_get(WB.format(code=code)))
        if not (isinstance(payload, list) and len(payload) == 2
                and isinstance(payload[1], list)):
            raise RuntimeError(f"world bank {code}: unexpected payload")
        cache_file.write_text(json.dumps(payload))
        time.sleep(1)
    return {int(o["date"]): o["value"] for o in payload[1]
            if o["value"] is not None}


# ---------------------------------------------------------------- checks

def check(label: str, got, want: float, tol: float) -> None:
    if got is None:
        raise SystemExit(f"  !! {label}: missing from the data")
    if abs(got - want) > tol:
        raise SystemExit(f"  !! {label} = {got}, expected {want} ± {tol}; "
                         f"not writing")
    print(f"  ok {label}: {got} (expected {want})")


def fresh(name: str, data: dict[str, float]) -> str:
    """Assert a monthly series reaches a recent month (the rendoblim trap)."""
    last = max(data)
    y, m = map(int, last.split("-"))
    today = dt.date.today()
    lag = (today.year - y) * 12 + today.month - m
    if lag > MAX_STALE_MONTHS:
        raise SystemExit(f"  !! {name} ends {last}, {lag} months ago — "
                         f"frozen cube? not writing")
    print(f"  ok {name} fresh: last month {last} ({lag} months back)")
    return last


def fmt(v, nd=4):
    if v is None:
        return ""
    return int(round(v)) if nd == 0 else round(v, nd)


def write(rel: str, comment: str, header: list[str], rows: list[list]) -> None:
    path = DATA / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        for line in comment.strip().splitlines():
            fh.write(f"# {line}".rstrip() + "\n")
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    span = f"{rows[0][0]}–{rows[-1][0]}" if rows else "EMPTY"
    print(f"  data/{rel}  {len(rows)} rows ({span})")


def months(first: str, last: str) -> list[str]:
    y, m = map(int, first.split("-"))
    ly, lm = map(int, last.split("-"))
    out = []
    while (y, m) <= (ly, lm):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def december_or_latest(data: dict[str, float], year: int):
    """(month used, value): December, or the latest month of a running year."""
    if f"{year}-12" in data:
        return f"{year}-12", data[f"{year}-12"]
    inyear = sorted(k for k in data if k.startswith(f"{year}-"))
    if inyear and year == int(max(data)[:4]):
        return inyear[-1], data[inyear[-1]]
    return "", None


# ---------------------------------------------------------------- plates

def policy_rate() -> None:
    pub, rows = cube("snboffzisa")
    lz, lo, hi = (series(rows, D0=k) for k in ("LZ", "UG0", "OG0"))
    check("libor target 2006-01 lower", lo.get("2006-01"), 0.5, 1e-9)
    check("libor target 2006-01 upper", hi.get("2006-01"), 1.5, 1e-9)
    check("libor target 2015-01 lower", lo.get("2015-01"), -1.25, 1e-9)
    check("policy rate 2019-06", lz.get("2019-06"), -0.75, 1e-9)
    check("policy rate 2022-12", lz.get("2022-12"), 1.0, 1e-9)
    check("policy rate 2025-06", lz.get("2025-06"), 0.0, 1e-9)
    if min(lz) != "2019-06" or max(lo) != "2019-05" or max(hi) != "2019-05":
        raise SystemExit(f"  !! instrument switch moved: LZ from {min(lz)}, "
                         f"Libor range to {max(lo)}")
    last = fresh("snboffzisa", lz)
    out = [[m, fmt(lz.get(m)), fmt(lo.get(m)), fmt(hi.get(m))]
           for m in months("2006-01", last)]
    write("markets/policy_rate_from_snb.csv", f"""
SNB official interest rates, cube snboffzisa (published {pub}), monthly, %.
TWO INSTRUMENTS, NEVER ONE LINE: libor_target_lower/upper = the SNB target
range for 3-month CHF Libor, to 2019-05; policy_rate = the SNB policy rate,
from 2019-06. A blank is a month in which that instrument did not exist.
""", ["month", "policy_rate", "libor_target_lower", "libor_target_upper"], out)


def fx() -> None:
    pub, rows = cube("devkum")
    _, annual = cube("devkua")
    s = {(d0, d1): series(rows, D0=d0, D1=d1)
         for d0 in ("M0", "M1") for d1 in ("EUR1", "USD1")}
    ea, ua = series(annual, D1="EUR1"), series(annual, D1="USD1")
    check("devkua EUR 2006", ea.get("2006"), 1.5729, 0.00005)
    check("devkua EUR 2015", ea.get("2015"), 1.0681, 0.00005)
    check("devkua EUR 2025", ea.get("2025"), 0.9370, 0.00005)
    check("devkua USD 2024", ua.get("2024"), 0.8801, 0.00005)
    check("devkua USD 2025", ua.get("2025"), 0.8307, 0.00005)
    check("devkum EUR 2011-09 avg (floor)", s["M0", "EUR1"].get("2011-09"), 1.2010, 0.00005)
    check("devkum EUR 2014-12 avg (floor)", s["M0", "EUR1"].get("2014-12"), 1.2024, 0.00005)
    check("devkum EUR 2015-01 avg (floor removed)", s["M0", "EUR1"].get("2015-01"), 1.0983, 0.00005)
    # Internal cross-check: the mean of the twelve monthly averages lands
    # on the annual average (computed by the SNB from daily rates).
    for year in range(Y0, 2026):
        for cur, ann in (("EUR1", ea), ("USD1", ua)):
            vals = [s["M0", cur][f"{year}-{m:02d}"] for m in range(1, 13)]
            if abs(statistics.fmean(vals) - ann[str(year)]) > 0.006:
                raise SystemExit(f"  !! {cur} {year}: monthly mean "
                                 f"{statistics.fmean(vals):.4f} vs annual "
                                 f"{ann[str(year)]:.4f}")
    print("  ok monthly averages agree with devkua annual averages 2006–2025")
    last = fresh("devkum", s["M0", "EUR1"])
    out = [[m, fmt(s["M0", "EUR1"].get(m)), fmt(s["M1", "EUR1"].get(m)),
            fmt(s["M0", "USD1"].get(m)), fmt(s["M1", "USD1"].get(m))]
           for m in months("2006-01", last)]
    write("markets/fx_from_snb.csv", f"""
SNB foreign exchange rates, cube devkum (published {pub}), monthly.
CHF PER 1 EUR / PER 1 USD: a RISING value is a WEAKER franc. *_avg = monthly
average, *_eom = end of month. The 1.20 EUR floor (2011-09-06) and its
removal (2015-01-15) are events in these rows. Annual averages (cube devkua)
are asserted against the monthly means by the fetcher, not written here.
""", ["month", "eur_chf_avg", "eur_chf_eom", "usd_chf_avg", "usd_chf_eom"], out)


def yields() -> None:
    pub, rows = cube("rendeiduebm")
    y2 = series(rows, D0="CHF", D1="2J")
    y10 = series(rows, D0="CHF", D1="10J")
    check("10y 2006-01", y10.get("2006-01"), 2.153, 1e-9)
    check("10y 2015-01", y10.get("2015-01"), -0.067, 1e-9)
    check("10y 2022-12", y10.get("2022-12"), 1.565, 1e-9)
    check("10y 2026-09", y10.get("2026-09"), 0.586, 1e-9)
    last = fresh("rendeiduebm", y10)
    # rendoblim is the stalled twin: it must agree where it exists, and its
    # end is reported so a reader can see why it is not the source.
    _, old = cube("rendoblim")
    o10 = series(old, D0="10J")
    common = sorted(set(o10) & set(y10))
    worst = max(abs(o10[m] - y10[m]) for m in common)
    if worst > 0.05:
        raise SystemExit(f"  !! rendoblim vs rendeiduebm differ by {worst}")
    print(f"  ok rendoblim agrees on {len(common)} months (max gap {worst:.3f}); "
          f"it ends {max(o10)}")
    out = [[m, fmt(y2.get(m), 3), fmt(y10.get(m), 3)]
           for m in months("2006-01", last)]
    write("markets/yields_from_snb.csv", f"""
SNB spot interest rates on Swiss Confederation bonds, cube rendeiduebm
(published {pub}), monthly, % (D0=CHF, maturities 2 and 10 years). NOT the
cube rendoblim, which froze at {max(o10)} while still answering HTTP 200 (it
matches this series to within {worst:.3f} pt where both exist).
""", ["month", "yield_2y", "yield_10y"], out)


def mortgage_rates() -> None:
    pub, rows = cube("zikreddet")
    pub2, rows2 = cube("zikrepro")
    keys = ("K", "OBB", "MBB", "FH", "FI")
    okeys = ("MV", "20", "50", "10", "31", "SARJ03")
    d = {k: series(rows, D0=k) for k in keys}
    o = {k: series(rows2, D0="M", D1=k) for k in okeys}
    # Where each series really starts. Asked WITHOUT fromDate, the API
    # answers only the last ~15 months, which once made zikrepro look like
    # a survey that began in 2025-08; it is a long series.
    starts = {"zikreddet FH": (min(d["FH"]), "2009-05"),
              "zikrepro MV": (min(o["MV"]), "1990-01"),
              "zikrepro 10y": (min(o["10"]), "2007-12"),
              "zikrepro SARON 3y": (min(o["SARJ03"]), "2021-01")}
    for label, (got, want) in starts.items():
        if got != want:
            raise SystemExit(f"  !! {label} now starts {got}, expected {want}")
    if max(o["31"]) != "2021-06":
        raise SystemExit(f"  !! Libor-linked offered rate now ends {max(o['31'])}")
    check("investment loans fixed 2026-07", d["FI"].get("2026-07"), 2.00, 0.005)
    check("offered variable mortgage 2006-01", o["MV"].get("2006-01"), 3.03, 0.005)
    check("offered variable mortgage 2025-08", o["MV"].get("2025-08"), 2.81, 0.005)
    check("offered fixed 10y 2025-08", o["10"].get("2025-08"), 1.87, 0.005)
    last = max(fresh("zikreddet", d["FH"]), fresh("zikrepro", o["MV"]))
    out = [[m] + [fmt(d[k].get(m), 3) for k in keys]
           + [fmt(o[k].get(m), 3) for k in okeys]
           for m in months("2006-01", last)]
    write("markets/mortgage_rates_from_snb.csv", f"""
SNB interest rates, %, monthly. TWO SURVEYS, NEVER JOINED.
new_*: rates on NEW loan agreements, cube zikreddet (published {pub}), from
2009-05; blank before (not published): current-account advances; variable
mortgages not linked / linked to a base rate; fixed-rate mortgages; fixed-rate
investment loans.
offered_*: rates OFFERED by banks, mean across banks, cube zikrepro (published
{pub2}): variable mortgage (from 1990); fixed 2, 5 and 10 years (from
2007-12); Libor-linked 3-year with 3-month Libor (2007-12 to 2021-06, ends
with Libor); SARON-linked 3-year (from 2021-01). Libor- and SARON-linked are
two columns, never one line. zikrepro values are rounded to two decimals up
to 2017-05 and carry full precision from 2017-06. Blank = not published.
""", ["month", "new_current_account_advances", "new_variable_mortgage_no_base",
      "new_variable_mortgage_base_linked", "new_fixed_mortgage",
      "new_investment_loan_fixed", "offered_variable_mortgage",
      "offered_fixed_2y", "offered_fixed_5y", "offered_fixed_10y",
      "offered_libor_3y", "offered_saron_3y"], out)

def household_credit_banks() -> dict[int, float]:
    pub, rows = cube("bakredsekbrm")
    t0, h, oth = (series(rows, D1=k, D3="AA") for k in ("T0", "H", "T2"))
    check("bank HH loans Dec-2006", t0.get("2006-12"), 524270, 0.5)
    check("bank HH mortgages Dec-2006", h.get("2006-12"), 483641, 0.5)
    check("bank HH loans Dec-2025", t0.get("2025-12"), 945300, 0.5)
    check("bank HH mortgages Dec-2025", h.get("2025-12"), 901510, 0.5)
    check("bank HH loans Aug-2026", t0.get("2026-08"), 967580, 0.5)
    for m, v in t0.items():
        if m in h and m in oth and abs(h[m] + oth[m] - v) > 2:
            raise SystemExit(f"  !! {m}: mortgages + other != total")
    # Breaks: month-on-month steps no credit cycle produces. Each known one
    # is named in the CSV comment; an unknown one stops the run.
    known = {("T0", "2006-09"), ("H", "2006-09"), ("T0", "2007-12"),
             ("T2", "2007-12"), ("H", "2026-04"), ("T2", "2026-04")}
    for key, ser in (("T0", t0), ("H", h), ("T2", oth)):
        ms = sorted(ser)
        for a, b in zip(ms, ms[1:]):
            if a >= "2006-01" and abs(ser[b] - ser[a]) > 10_000 \
                    and (key, b) not in known:
                raise SystemExit(f"  !! {key} steps {ser[b] - ser[a]:+,.0f} in {b}: "
                                 f"new reclassification? not writing")
    print("  ok no unexplained month-on-month step above CHF 10bn since 2006 "
          "(known: 2006-09, 2007-12, 2026-04)")
    fresh("bakredsekbrm", t0)
    out, dec = [], {}
    for year in range(Y0, Y1 + 1):
        month, v = december_or_latest(t0, year)
        if not month:
            continue
        dec[year] = v
        out.append([year, month, fmt(v, 0), fmt(h.get(month), 0),
                    fmt(oth.get(month), 0)])
    write("credit/household_credit_banks_from_snb.csv", f"""
SNB, domestic loans by economic activity: PRIVATE HOUSEHOLDS (cube
bakredsekbrm, D3=AA, published {pub}). STOCKS, CHF millions, BANKS ONLY
(loans from banks in the SNB reporting population; whether Liechtenstein is
inside that population is unconfirmed, an open question). One reading per year: the
December stock (`month` says which), or the latest month for the running
year. Never sum months. The monthly stock steps +CHF 60bn between 2006-08 and
2006-09 (reporting change); every row here is after it. Other loans drop
CHF 10bn in the single month 2007-12 (unexplained in the cube; the Dec-2007
row carries it). BREAK 2026-04: about
CHF 17bn moved from mortgages to other loans while the total rose CHF 2bn (a
reclassification, not new lending), so the 2026 split is not comparable with
2025; the total is. other = loans other than mortgages (secured +
unsecured); total = mortgages + other.
All-lender totals are household_debt_fa_from_snb.csv (cube from 1999).
""", ["year", "month", "loans_total", "mortgages", "other_loans"], out)
    return dec


def household_debt_fa(banks: dict[int, float]) -> None:
    pub, rows = cube("frsekgevehup")
    pub2, rows2 = cube("frsekphupooe")
    t5, hyp, kon, ukr = (series(rows, D1=k) for k in ("T5", "HYP", "KON", "UKR"))
    hn = series(rows2, D0="BES", D1="T5", D2="T6", D3="T7")
    ph = series(rows2, D0="BES", D1="T5", D2="T6", D3="PH")
    # The cube runs from 1999; asked without fromDate the API answers only
    # the last ten years, which once made it look as if it began in 2016.
    if min(t5) != str(Y0) or min(hn) != str(Y0):
        raise SystemExit(f"  !! financial accounts start {min(t5)}/{min(hn)}, "
                         f"not {Y0}")
    check("FA HH loans 2016", t5.get("2016"), 825150, 0.5)
    check("FA HH loans 2025", t5.get("2025"), 1050981, 0.5)
    check("FA HH mortgages 2025", hyp.get("2025"), 983072, 0.5)
    check("FA HH consumer loans 2025", kon.get("2025"), 20679, 0.5)
    check("FA HH+NPISH loans 2025 (CHF bn)", round(hn.get("2025", 0) / 1000, 1), 1066.8, 0.05)
    for y in t5:
        if abs(t5[y] - ph.get(y, -1)) > 0.5:
            raise SystemExit(f"  !! {y}: frsekgevehup != frsekphupooe PH")
        if abs(hyp[y] + kon[y] + ukr[y] - t5[y]) > 2:
            raise SystemExit(f"  !! {y}: loan components do not add up")
        gap = t5[y] - banks.get(int(y), float("nan"))
        if not 30_000 < gap < 150_000:
            raise SystemExit(f"  !! {y}: all-lender minus bank-only = {gap:,.0f}")
    print("  ok FA households sit CHF 30–150bn above bank-only loans every year "
          f"(2025 gap {t5['2025'] - banks[2025]:,.0f} mn)")
    # Second publisher: Eurostat nasa_10_f_bs (S14_S15, F4 liabilities, CHF
    # mn), which the SNB transmits; the levels must match to rounding.
    es = estat_hh_loans()
    for y, v in hn.items():
        if y in es and abs(es[y] / v - 1) > 0.005:
            raise SystemExit(f"  !! {y}: SNB HH+NPISH {v:,.0f} vs Eurostat "
                             f"{es[y]:,.0f}")
    print(f"  ok HH+NPISH loans equal Eurostat nasa_10_f_bs within 0.5% "
          f"({len(set(hn) & set(es))} years)")
    out = [[y, fmt(t5[y], 0), fmt(hyp.get(y), 0), fmt(kon.get(y), 0),
            fmt(ukr.get(y), 0), fmt(hn.get(y), 0)] for y in sorted(t5)]
    write("credit/household_debt_fa_from_snb.csv", f"""
SNB financial accounts, balance sheet of households (cube frsekgevehup,
published {pub}; HH+NPISH from frsekphupooe, published {pub2}). Year-end
STOCKS, CHF millions, loans from ALL lenders (banks, insurers, pension funds,
others). The cube runs from 1999 (consumer and other loans from 2005); rows
here are the atlas window from {Y0}. HH+NPISH levels equal Eurostat
nasa_10_f_bs (asserted); Eurostat's % GDP ratio is on the OLD GDP vintage and
is a separate file. loans_total = mortgages + consumer_loans (incl. leasing) +
other_loans, households only; loans_hh_npish adds non-profit institutions
serving households. About CHF 100bn above the bank-only series: two
definitions, two lines.
""", ["year", "loans_total", "mortgages", "consumer_loans", "other_loans",
      "loans_hh_npish"], out)


def estat_hh_loans() -> dict[str, float]:
    cache_file = CACHE / "snb_xcheck_estat_nasa_hh_loans.json"
    if cache_file.exists():
        payload = json.loads(cache_file.read_text())
    else:
        payload = json.loads(_get(ESTAT))
        if "value" not in payload or "dimension" not in payload:
            raise RuntimeError("eurostat nasa_10_f_bs: unexpected payload")
        cache_file.write_text(json.dumps(payload))
    idx = payload["dimension"]["time"]["category"]["index"]
    return {y: payload["value"][str(i)] for y, i in idx.items()
            if str(i) in payload["value"]}


def reserves() -> None:
    pub, rows = cube("snbimfra")
    chf, usd = series(rows, D0="T1", D1="T0"), series(rows, D0="T1", D1="T1")
    gchf, gusd = series(rows, D0="T7", D1="T0"), series(rows, D0="T7", D1="T1")
    check("reserves USD Dec-2006 (bn)", round(usd["2006-12"] / 1000, 1), 64.5, 0.05)
    check("reserves USD Dec-2014 (bn)", round(usd["2014-12"] / 1000, 1), 545.4, 0.05)
    check("reserves USD Dec-2021 (bn)", round(usd["2021-12"] / 1000, 1), 1110.0, 0.05)
    check("reserves USD Dec-2025 (bn)", round(usd["2025-12"] / 1000, 1), 1075.1, 0.05)
    # Second publisher: World Bank FI.RES.TOTL.CD (IMF IFS, incl. gold).
    wbres = wb("FI.RES.TOTL.CD")
    for year in (2010, 2015, 2020, 2024, 2025):
        if year in wbres:
            ratio = usd[f"{year}-12"] * 1e6 / wbres[year]
            if abs(ratio - 1) > 0.02:
                raise SystemExit(f"  !! reserves {year}: SNB/WB = {ratio:.3f}")
    print("  ok SNB December reserves within 2% of World Bank FI.RES.TOTL.CD")
    fresh("snbimfra", usd)
    out = []
    for year in range(Y0, Y1 + 1):
        month, v = december_or_latest(usd, year)
        if month:
            out.append([year, month, fmt(chf.get(month), 0), fmt(v, 0),
                        fmt(gchf.get(month), 0), fmt(gusd.get(month), 0)])
    write("international/reserves_from_snb.csv", f"""
SNB, Switzerland's international reserves, IMF reserves template section 1
(cube snbimfra, published {pub}). A. OFFICIAL RESERVE ASSETS (T1), and of which
gold incl. gold deposits and swaps (T7). STOCKS in CHF millions and USD
millions at the reading month: December, or the latest month of the running
year (`month`). Never sum months. Checked within 2% of the World Bank's
FI.RES.TOTL.CD.
""", ["year", "month", "reserves_chf_mn", "reserves_usd_mn", "gold_chf_mn",
      "gold_usd_mn"], out)


def current_account() -> None:
    pub, rows = cube("bopcurra")
    s = defaultdict(dict)
    for r in rows:
        if r["Value"]:
            s[(r["D0"], r["D1"])][int(r["Date"])] = float(r["Value"])
    bn = lambda k, e, y: round(s[(k, e)].get(y, 0) / 1000, 1)  # noqa: E731
    check("BoP 2024 foreign trade receipts (bn)", bn("T1", "E", 2024), 393.8, 0.05)
    check("BoP 2024 foreign trade total 1 receipts (bn)", bn("DAT1", "E", 2024), 283.0, 0.05)
    check("BoP 2024 non-monetary gold receipts (bn)", bn("DGZ", "E", 2024), 94.1, 0.05)
    check("BoP 2025 foreign trade receipts (bn)", bn("T1", "E", 2025), 461.0, 0.05)
    check("BoP 2025 non-monetary gold receipts (bn)", bn("DGZ", "E", 2025), 149.6, 0.05)
    check("BoP 2025 non-monetary gold expenses (bn)", bn("DGZ", "A", 2025), 173.7, 0.05)
    check("BoP 2024 merchanting (bn)", bn("T3", "S", 2024), 62.5, 0.05)
    check("BoP 2024 current account (bn)", bn("L0", "S", 2024), 79.8, 0.05)
    check("BoP 2025 current account (bn)", bn("L0", "S", 2025), 49.6, 0.05)
    years = sorted(s[("L0", "S")])
    # The cube runs from 1983; asked without fromDate the API answers only
    # the last ten years, which once made it look as if it began in 2016.
    if years[0] != Y0:
        raise SystemExit(f"  !! bopcurra rows start {years[0]}, not {Y0}")
    for y in years:
        net = s[("L0", "E")][y] - s[("L0", "A")][y]
        if abs(net - s[("L0", "S")][y]) > 2:
            raise SystemExit(f"  !! {y}: receipts - expenses != balance")
    # Second publisher: World Bank BN.CAB.XOKA.CD (USD), converted with the
    # SNB annual USD rate. The WB lags SNB revisions, hence 10%.
    _, annual = cube("devkua")
    usd = series(annual, D1="USD1")
    wbca = wb("BN.CAB.XOKA.CD")
    tested = 0
    for y in years:
        if y in wbca and str(y) in usd:
            snb_usd = s[("L0", "S")][y] / usd[str(y)] * 1e6
            # 10%, or USD 5bn where the balance is near zero (2020).
            if abs(snb_usd - wbca[y]) > max(0.10 * abs(wbca[y]), 5e9):
                raise SystemExit(f"  !! CA {y}: SNB {snb_usd/1e9:.1f} vs "
                                 f"WB {wbca[y]/1e9:.1f} USD bn")
            tested += 1
    if not tested:
        raise SystemExit("  !! no World Bank current-account year to compare")
    print(f"  ok current account within 10% (or USD 5bn) of World Bank BN.CAB.XOKA.CD "
          f"({tested} years)")
    cols = [("L0", "E"), ("L0", "A"), ("L0", "S"), ("T0", "E"), ("T0", "A"),
            ("T1", "E"), ("T1", "A"), ("DAT1", "E"), ("DAT1", "A"),
            ("DGZ", "E"), ("DGZ", "A"), ("T3", "S"), ("T4", "E"), ("T4", "A"),
            ("T7", "S"), ("T9", "S")]
    out = [[y] + [fmt(s[c].get(y), 1) for c in cols] for y in years]
    write("trade/current_account_from_snb.csv", f"""
SNB, Swiss balance of payments, current account, annual (cube bopcurra,
published {pub}). CHF millions, BoP basis (never spliced with the BAZG
customs file). The cube runs from 1983; rows here are the atlas window from
{Y0}. Scope: Liechtenstein inclusion unconfirmed (open question).
GOLD: goods_trade_* = foreign trade total INCLUDING non-monetary gold;
goods_trade_total1_* = foreign trade "Total 1" EXCLUDING gold, precious
metals, gems, art and antiques; gold_* = non-monetary gold. goods_* = all
goods incl. supplements and merchanting. Receipts and expenses are separate;
*_balance = receipts - expenses (merchanting is net).
""", ["year", "ca_receipts", "ca_expenses", "ca_balance", "goods_receipts",
      "goods_expenses", "goods_trade_receipts", "goods_trade_expenses",
      "goods_trade_total1_receipts", "goods_trade_total1_expenses",
      "gold_receipts", "gold_expenses", "merchanting_net",
      "services_receipts", "services_expenses", "primary_income_balance",
      "secondary_income_balance"], out)


def main() -> None:
    print("SNB (data.snb.ch cube API)")
    policy_rate()
    fx()
    yields()
    mortgage_rates()
    banks = household_credit_banks()
    household_debt_fa(banks)
    reserves()
    current_account()


if __name__ == "__main__":
    main()
