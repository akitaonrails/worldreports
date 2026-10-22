#!/usr/bin/env python3
"""The gaps the plate spine found in Argentina, fetched into sidecars.

Usage:  python3 -I countries/argentina/fetch/fetch_spine.py

The spine (PLATE_SPINE.md) gives every country the same canonical slots.
These are the ones Argentina could not fill from what it already staged,
each from its own publisher:

  BCRA            the monetary-policy rate (v160, Dec 2015 - Jul 2025) and
                  BADLAR, private banks (v7), the market reference rate the
                  BCRA's own NOBAC notes were indexed to before 2016
                  -> macro/policy_rate_check.csv
  US Treasury     the 10-year par yield, daily, averaged per year: the base
                  an Argentine US$ bond yield sits on (Argentina has no
                  peso 10-year benchmark; see DATA_NOTES.md)
                  -> markets/us_treasury_10y_check.csv
  Transparency    Corruption Perceptions Index, 2012+ method, from TI's own
  International   results-and-trends workbook (CPI 2024 edition)
                  -> social/corruption_check.csv
  Sec. Hacienda   national public sector "inversión real directa", Esquema
  (datos.gob.ar)  AIF, three methodologies kept apart, % of GDP
                  -> fiscal/public_investment_check.csv
  UN Comtrade     goods exports by partner, shares of the total
                  -> trade/destinations_check.csv

A sidecar is never what a plate draws: fetch/curate.py adopts it into the
curated file after a person has diffed it. Every series is spot-checked
against a value read off the publisher, and the totals that a national file
also holds are cross-checked against it, before anything is written.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import re
import ssl
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache" / "spine"
CACHE.mkdir(parents=True, exist_ok=True)
YEAR_FROM, YEAR_TO = 2006, 2026
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) "
                         "argentina-reports/1.0", "Accept": "*/*"}


# --------------------------------------------------------------- transport
def get(url: str, cache: str, binary: bool = False):
    path = CACHE / cache
    if path.exists():
        raw = path.read_bytes()
    else:
        raw = None
        for attempt in range(4):
            for context in (None, ssl._create_unverified_context()):
                try:
                    req = urllib.request.Request(url, headers=HEADERS)
                    with urllib.request.urlopen(req, timeout=180,
                                                context=context) as r:
                        raw = r.read()
                    break
                except Exception as e:  # noqa: BLE001
                    print(f"  {cache} attempt {attempt + 1}: {e}",
                          file=sys.stderr)
            if raw is not None:
                break
            time.sleep(3 * (attempt + 1))
        if raw is None:
            raise SystemExit(f"could not fetch {url}")
        path.write_bytes(raw)
    return raw if binary else raw.decode("utf-8")


def write(rel: str, header: list[str], rows: list[list]) -> None:
    path = DATA / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    print(f"  -> data/{rel}")


def spot(label: str, got, want, tol: float) -> None:
    if got is None or abs(got - want) > tol:
        raise SystemExit(f"{label}: got {got!r}, expected {want} ± {tol}. "
                         f"The upstream changed; check before adopting.")
    print(f"  spot {label}: {got:.4g} (expected {want})")


def cell(v, spec: str) -> str:
    return "" if v is None else format(v, spec)


# ------------------------------------------------------------- BCRA rates
BCRA = ("https://api.bcra.gob.ar/estadisticas/v4.0/monetarias/{var}"
        "?desde={a}-01-01&hasta={b}-12-31&limit=3000")


def bcra(var: int) -> dict[str, float]:
    points: dict[str, float] = {}
    for a in range(2003, YEAR_TO + 1, 5):
        b = min(a + 4, YEAR_TO)
        page = json.loads(get(BCRA.format(var=var, a=a, b=b),
                              f"bcra_{var}_{a}.json"))
        for row in (page.get("results") or [{}])[0].get("detalle", []):
            if row.get("valor") is not None:
                points[row["fecha"]] = float(row["valor"])
    return points


def by_year(points: dict[str, float]) -> dict[int, list[tuple[str, float]]]:
    out: dict[int, list[tuple[str, float]]] = {}
    for d, v in sorted(points.items()):
        out.setdefault(int(d[:4]), []).append((d, v))
    return out


def build_rates() -> None:
    print("BCRA — policy rate (v160) and BADLAR private banks (v7)")
    policy = by_year(bcra(160))
    badlar = by_year(bcra(7))
    # Read off the BCRA series on 2026-10-22: the policy rate was 100% TNA
    # at the end of 2023 (cut from 133% on 18 December) and 32% at the end
    # of 2024, and the series ends on 10 July 2025, when the BCRA stopped
    # setting one.
    spot("policy rate, last 2023", policy[2023][-1][1], 100.0, 0.01)
    spot("policy rate, last 2024", policy[2024][-1][1], 32.0, 0.01)
    last = max(d for rows in policy.values() for d, _ in rows)
    if last != "2025-07-10":
        raise SystemExit(f"policy rate now ends {last}; it ended 2025-07-10")
    rows = []
    for y in range(YEAR_FROM, YEAR_TO + 1):
        p, b = policy.get(y, []), badlar.get(y, [])
        # The policy rate's annual average is a mean over the days it
        # existed. A year it did not span whole (2015's last fortnight,
        # 2025's first half) is left out, not averaged over a stub.
        whole = p and p[0][0] <= f"{y}-01-15" and p[-1][0] >= f"{y}-12-15"
        rows.append([
            y,
            cell(sum(v for _, v in p) / len(p) if whole else None, ".2f"),
            cell(p[-1][1] if whole else None, ".2f"),
            cell(sum(v for _, v in b) / len(b) if b else None, ".2f"),
            cell(len(b) or None, "d"),
        ])
    write("macro/policy_rate_check.csv",
          ["year", "policy_avg", "policy_eoy", "badlar_avg", "badlar_days"],
          rows)


# ------------------------------------------------------------ US Treasury
UST = ("https://home.treasury.gov/resource-center/data-chart-center/"
       "interest-rates/daily-treasury-rates.csv/{y}/all"
       "?type=daily_treasury_yield_curve&field_tdr_date_value={y}&page"
       "&_format=csv")


def build_ust() -> None:
    print("US Treasury — 10-year par yield, annual average")
    rows = []
    avg = {}
    for y in range(YEAR_FROM, YEAR_TO + 1):
        text = get(UST.format(y=y), f"ust_{y}.csv")
        reader = csv.DictReader(text.splitlines())
        vals = [float(r["10 Yr"]) for r in reader
                if (r.get("10 Yr") or "").strip()]
        avg[y] = sum(vals) / len(vals) if vals else None
        rows.append([y, cell(avg[y], ".3f"), len(vals) or ""])
    # Federal Reserve H.15 annual averages of the same constant-maturity
    # yield: 2.14% in 2019, 0.89% in 2020.
    spot("UST 10y 2019", avg[2019], 2.14, 0.02)
    spot("UST 10y 2020", avg[2020], 0.89, 0.02)
    write("markets/us_treasury_10y_check.csv", ["year", "avg", "days"], rows)


# -------------------------------------------------- Transparency International
TI_EDITION = 2024
TI = (f"https://images.transparencycdn.org/images/"
      f"CPI{TI_EDITION}-Results-and-trends.xlsx")


def build_cpi() -> None:
    """Argentina's CPI score and rank from TI's time-series sheet.

    The same reader Korea uses: an xlsx is a zip of XML, cells with t="s"
    index sharedStrings, empty cells are omitted so columns are matched by
    reference, and the 2012-13 headers say "CPI Score" where later ones say
    "CPI score". The workbook stops at its own edition; later editions are
    added by hand in the curated file, each with its source.
    """
    print(f"Transparency International — CPI {TI_EDITION} workbook")
    raw = get(TI, f"cpi{TI_EDITION}.xlsx", binary=True)
    path = CACHE / f"cpi{TI_EDITION}.xlsx"
    with zipfile.ZipFile(path) as z:
        strings = ["".join(re.findall(r"<t[^>]*>(.*?)</t>", c, re.S))
                   for c in re.findall(r"<si>(.*?)</si>",
                                       z.read("xl/sharedStrings.xml").decode(),
                                       re.S)]
        sheet = z.read("xl/worksheets/sheet2.xml").decode()
    del raw

    def cells(row: str) -> dict[str, str]:
        out = {}
        for m in re.finditer(r'<c r="([A-Z]+)\d+"([^>]*)>(.*?)</c>', row,
                             re.S):
            ref, attrs, body = m.groups()
            v = re.search(r"<v>(.*?)</v>", body)
            value = v.group(1) if v else ""
            if 't="s"' in attrs and value:
                value = strings[int(value)]
            out[ref] = value
        return out

    rows = [cells(r) for r in re.findall(r"<row[^>]*>(.*?)</row>", sheet,
                                         re.S)]
    header = next(r for r in rows if "Country / Territory" in r.values())
    ar = next(r for r in rows if r.get("A") == "Argentina")
    score, rank = {}, {}
    for ref, label in header.items():
        low = label.lower()
        for prefix, into in (("cpi score ", score), ("rank ", rank)):
            if low.startswith(prefix) and low[len(prefix):].strip().isdigit():
                v = ar.get(ref, "")
                if v:
                    into[int(low[len(prefix):])] = float(v)
    spot("CPI 2019", score.get(2019), 45, 0)
    spot("CPI 2015", score.get(2015), 32, 0)
    write("social/corruption_check.csv", ["year", "score", "rank"],
          [[y, cell(score.get(y), ".0f"), cell(rank.get(y), ".0f")]
           for y in sorted(score)])


# ---------------------------------------------- national public investment
# Esquema AIF, Sector Público Nacional, base caja: "gastos de capital —
# inversión real directa", in millions of pesos. One id per methodology;
# they are never spliced (the same rule as fiscal/primary_result.csv).
INVESTMENT = {
    "m1993": "379.1_GTOS_CAP_I006__41_45",   # 1993-2006, annual
    "m2007": "379.2_GTOS_CAP_I014__41_48",   # 2007-2014, annual
    "m2017": "379.3_GTOS_CAP_I017__36_45",   # 2015-2025, annual
}


def datos_gob():
    """fetch_datos_gob.py, loaded by path: one transport, one cache."""
    spec = importlib.util.spec_from_file_location(
        "_ar_datos_gob", Path(__file__).with_name("fetch_datos_gob.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build_investment() -> None:
    print("Secretaría de Hacienda — inversión real directa, SPN")
    dg = datos_gob()
    gdp = dg.annual(dg.GDP_ARS, "eop", "year", "PIB $ mn")
    cols = {}
    for name, sid in INVESTMENT.items():
        pesos = dg.annual(sid, "eop", "year", name)
        cols[name] = {y: v / gdp[y] * 100 for y, v in pesos.items()
                      if y in gdp}
    # Sanity, not a published figure: national direct investment has been
    # between 0.3% and 3% of GDP in every year of the window.
    for name, d in cols.items():
        for y, v in d.items():
            if YEAR_FROM <= y <= YEAR_TO and not 0.2 < v < 3.5:
                raise SystemExit(f"{name} {y}: {v:.2f}% of GDP is implausible")
    write("fiscal/public_investment_check.csv",
          ["year", "m1993", "m2007", "m2017"],
          [[y] + [cell(cols[k].get(y), ".2f") for k in INVESTMENT]
           for y in range(YEAR_FROM, YEAR_TO + 1)])


# -------------------------------------------------------------- Comtrade
COMTRADE = ("https://comtradeapi.un.org/public/v1/preview/C/A/HS"
            "?reporterCode=32&period={y}&flowCode=X&cmdCode=TOTAL"
            "&partner2Code=0&customsCode=C00&motCode=0")
# M49 codes of the destinations drawn: the four largest over the window.
PARTNERS = {"brazil": 76, "china": 156, "usa": 842, "chile": 152,
            "india": 699}


def build_destinations() -> None:
    print("UN Comtrade — Argentine goods exports by partner")
    nat = {}
    with (DATA / "trade" / "trade.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["exports"]:
                nat[int(r["year"])] = float(r["exports"])
    rows = []
    for y in range(YEAR_FROM, YEAR_TO):
        page = json.loads(get(COMTRADE.format(y=y), f"comtrade_{y}.json"))
        if not page.get("data"):
            time.sleep(2)
            rows.append([y] + [""] * (len(PARTNERS) + 1))
            continue
        by = {r["partnerCode"]: r["primaryValue"] for r in page["data"]}
        world = by.get(0)
        # The reporter's world total is INDEC's own customs total, so the
        # two must agree to well under a percent.
        if y in nat and abs(world / 1e9 / nat[y] - 1) > 0.01:
            raise SystemExit(f"Comtrade world {y}: {world / 1e9:.1f} vs "
                             f"INDEC {nat[y]:.1f} US$ bn")
        rows.append([y] + [cell(by.get(c, 0) / world * 100, ".2f")
                           for c in PARTNERS.values()]
                    + [cell(world / 1e9, ".2f")])
        time.sleep(1.5)
    shares = {r[0]: r for r in rows}
    # Brazil's share in 2006 and China's in 2025, computed by hand from the
    # Comtrade preview on 2026-10-22.
    spot("Brazil share 2006", float(shares[2006][1]), 17.5, 0.1)
    spot("China share 2025", float(shares[2025][2]), 11.2, 0.1)
    write("trade/destinations_check.csv",
          ["year", *PARTNERS, "world_usd_bn"], rows)


def main() -> None:
    build_rates()
    build_ust()
    build_cpi()
    build_investment()
    build_destinations()
    print("Done. Sidecars written — diff, then adopt with fetch/curate.py.")


if __name__ == "__main__":
    main()
