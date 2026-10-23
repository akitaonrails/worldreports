#!/usr/bin/env python3
"""Refresh the Banco de Portugal (BPstat) series into sidecar CSVs.

Usage:  python3 -I countries/portugal/fetch/fetch_bpstat.py

BPstat's public API needs no key. Two calls do everything:

  /data/v1/series/?series_ids={ids}&lang=EN
      metadata — label, domain_ids, dataset_id, and the series'
      coordinates in its dataset cube (`dimension_category`)
  /data/v1/domains/{dom}/datasets/{dsid}/?series_ids={ids}&lang=EN
      observations — JSON-stat 2.0, time dimension `reference_date`

Series drawn (IDs verified live 2026-10-22, see DISCOVERY.md):

  12099464  10y Treasury-bond (OT) yield, Portugal, monthly avg, %
  12560098  10y government-bond yield, Germany, same dataset (the spread)
  12533735  rate on new housing loans to households (long compilation)
  12710779  percentile-based new-business rate, variable-rate housing
  12457924  household indebtedness, €mn (monthly stock)
  12458135  household housing loans, % GDP
  12458131  household consumption & other loans, % GDP
  12504544  banking-sector NPL ratio (FSI, quarterly)
  88873/88884/88894, 12560947/12560959/12560943 and tax/interest detail
            Budget Outturn (domain 10, DGO via BPstat), cash basis
  12561512  Maastricht GG debt % GDP (domain 28) — CROSS-CHECK only

Things this API will do to you if nobody writes them down:

**Trailing slashes are mandatory.** `/series?...` without the slash is
a redirect/404, not the data.

**The dataset endpoint PAGINATES at ten series** and says so only in
`extension.next_page`. Ask for eleven series and the eleventh silently
is not there; every page is followed here, and every requested series
must come back.

**Values are a dense list over the cartesian cube.** The Budget Outturn
cube is 7 items × 2 sectors, but not every item exists for both sectors
— those cells are null. A series is located by its own
`dimension_category` coordinates, never by position in the request.

**The Budget Outturn is YEAR-TO-DATE.** Metric 3657 "Year to date
values": the December reading IS the year; summing the months counts
January twelve times. The running year is its latest month, labelled
with the month in `as_of`. Cash basis, public-accounts criteria — the
national layer, beside the Eurostat EDP (accrual) deficit and never
spliced onto it.

**Stocks are read, not summed.** Household debt and NPLs are stocks:
a year is its December / Q4 reading (latest reading for the running
year, labelled). Means are only taken over complete years.

The X-Throttle header is recorded; requests are spaced and a 429 backs
off on Retry-After.

Outputs: data/markets/yield_10y_from_bpstat.csv,
         data/markets/mortgage_rate_from_bpstat.csv,
         data/credit/household_debt_from_bpstat.csv,
         data/credit/npl_from_bpstat.csv,
         data/fiscal/budget_outturn_from_bpstat.csv
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eurostat import strides  # noqa: E402  (shared JSON-stat stride rule)

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache"

API = "https://bpstat.bportugal.pt/data/v1"
Y0, Y1 = 2006, 2026
SPACING = 1.5          # seconds between live requests
UA = "worldreports-fetch/1.0 (+official-statistics plates)"

_last_call = 0.0


# --------------------------------------------------------------------- HTTP
def get(url: str, cache_name: str) -> dict | list:
    """GET a BPstat JSON document, cached under cache/ by name."""
    global _last_call
    CACHE.mkdir(exist_ok=True)
    path = CACHE / cache_name
    if path.exists():
        return json.loads(path.read_text())
    assert "/?" in url or url.endswith("/"), f"trailing slash missing: {url}"
    last = None
    for attempt in range(5):
        wait = SPACING - (time.monotonic() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.monotonic()
        try:
            req = urllib.request.Request(
                url, headers={"Accept": "application/json", "User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                throttle = r.headers.get("X-Throttle")
                raw = r.read()
            if throttle is not None and throttle.isdigit() \
                    and int(throttle) < 20:
                time.sleep(10)          # budget nearly spent: slow down
            payload = json.loads(raw)
            # An error document is a dict with "detail" or a field-error
            # map; neither has the shapes below. Never cache it.
            if not (isinstance(payload, list) or "value" in payload
                    or "link" in payload):
                raise ValueError(f"unexpected payload: {str(payload)[:200]}")
            path.write_text(json.dumps(payload))
            return payload
        except urllib.error.HTTPError as e:
            last = e
            retry = e.headers.get("Retry-After") if e.headers else None
            time.sleep(float(retry) if retry and retry.isdigit()
                       else 5 * (attempt + 1))
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"bpstat {url}: {last}")


def metadata(ids: list[int]) -> dict[int, dict]:
    q = ",".join(map(str, sorted(ids)))
    rows = get(f"{API}/series/?series_ids={q}&lang=EN",
               f"bpstat_meta_{q.replace(',', '_')}.json")
    out = {int(s["id"]): s for s in rows}
    missing = set(ids) - set(out)
    assert not missing, f"bpstat metadata missing {missing}"
    return out


def observations(ids: list[int]) -> dict[int, list[tuple[str, float]]]:
    """{series id: [(iso date, value)] ascending}, nulls dropped."""
    meta = metadata(ids)
    groups: dict[tuple[int, str], list[int]] = {}
    for sid in ids:
        m = meta[sid]
        groups.setdefault((m["domain_ids"][0], m["dataset_id"]), []).append(sid)
    out: dict[int, list[tuple[str, float]]] = {}
    for (dom, dsid), sids in groups.items():
        q = ",".join(map(str, sorted(sids)))
        url = (f"{API}/domains/{dom}/datasets/{dsid}/"
               f"?series_ids={urllib.parse.quote(q)}&lang=EN")
        page = 1
        while url:
            doc = get(url, f"bpstat_obs_{dom}_{dsid[:8]}_{q.replace(',', '_')}"
                           f"_p{page}.json")
            for sid, pairs in decode(doc).items():
                if sid in sids:
                    out.setdefault(sid, []).extend(pairs)
            url = doc.get("extension", {}).get("next_page")
            page += 1
    missing = [s for s in ids if not out.get(s)]
    assert not missing, f"bpstat: no observations for {missing}"
    return {s: sorted(set(out[s])) for s in ids}


def decode(doc: dict) -> dict[int, list[tuple[str, float]]]:
    """Locate each listed series in the JSON-stat cube by its coordinates."""
    ids, size, values = doc["id"], doc["size"], doc["value"]
    assert ids[-1] == "reference_date", ids
    # JSON-stat allows both a dense list over the whole cube and a sparse
    # {flat index: value} map; BPstat sends either, per dataset.
    if isinstance(values, dict):
        values = {int(k): v for k, v in values.items()}
    else:
        assert len(values) == _prod(size), (len(values), size)
        values = dict(enumerate(values))
    pos = []
    for dim in ids:
        index = doc["dimension"][dim]["category"]["index"]
        pos.append({str(c): i for i, c in enumerate(index)} if
                   isinstance(index, list) else
                   {str(c): i for c, i in index.items()})
    dates = doc["dimension"]["reference_date"]["category"]["index"]
    st = strides(size)
    out = {}
    for s in doc["extension"]["series"]:
        coord = {str(dc["dimension_id"]): str(dc["category_id"])
                 for dc in s["dimension_category"]}
        base = sum(pos[i][coord[d]] * st[i] for i, d in enumerate(ids[:-1]))
        out[int(s["id"])] = [(dates[t], float(values[base + t]))
                             for t in range(size[-1])
                             if values.get(base + t) is not None]
    return out


def _prod(xs: list[int]) -> int:
    n = 1
    for x in xs:
        n *= x
    return n


def cube_labels(dom: int, dsid: str, sid: int) -> dict[str, str]:
    """{dimension label: category label} for one series (for asserts)."""
    for page in sorted(CACHE.glob(f"bpstat_obs_{dom}_{dsid[:8]}_*_p*.json")):
        doc = json.loads(page.read_text())
        meta = next((s for s in doc["extension"]["series"]
                     if s["id"] == sid), None)
        if meta:
            break
    else:
        raise AssertionError(f"series {sid} not in any cached page")
    out = {}
    for dc in meta["dimension_category"]:
        dim = doc["dimension"][str(dc["dimension_id"])]
        out[dim["label"]] = dim["category"]["label"][str(dc["category_id"])]
    return out


# ------------------------------------------------------------ aggregation
def by_year(pairs):
    out: dict[int, list[tuple[str, float]]] = {}
    for d, v in pairs:
        out.setdefault(int(d[:4]), []).append((d, v))
    return out


def annual_mean(pairs, per_year: int = 12) -> dict[int, float]:
    """Mean over COMPLETE years only — a running year is left blank."""
    return {y: sum(v for _, v in obs) / len(obs)
            for y, obs in by_year(pairs).items()
            if Y0 <= y <= Y1 and len(obs) == per_year}


def year_end(pairs) -> tuple[dict[int, float], dict[int, str]]:
    """Last reading of each year (Dec / Q4, or latest for the running
    year) and the date it was read at — a stock or a YTD flow is READ."""
    vals, asof = {}, {}
    for y, obs in by_year(pairs).items():
        if Y0 <= y <= Y1:
            d, v = max(obs)
            vals[y], asof[y] = v, d[:7]
    return vals, asof


def at(pairs, date_prefix: str) -> float:
    hits = [v for d, v in pairs if d.startswith(date_prefix)]
    assert len(hits) == 1, (date_prefix, hits)
    return hits[0]


def write(rel: str, comments: list[str], header: list[str],
          columns: list[dict], fmts: list[str]) -> int:
    path = DATA / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {c}" for c in comments] + [",".join(["year"] + header)]
    for y in range(Y0, Y1 + 1):
        cells = []
        for col, fmt in zip(columns, fmts):
            v = col.get(y)
            cells.append("" if v is None else
                         (v if isinstance(v, str) else fmt.format(v)))
        lines.append(f"{y}," + ",".join(cells))
    path.write_text("\n".join(lines) + "\n")
    print(f"  -> data/{rel} ({Y1 - Y0 + 1} rows)")
    return Y1 - Y0 + 1


# ------------------------------------------------------------------ panels
def yields() -> None:
    obs = observations([12099464, 12560098])
    pt, de = obs[12099464], obs[12560098]
    meta = metadata([12099464, 12560098])
    assert "10 years" in meta[12099464]["label"], meta[12099464]["label"]
    assert "Germany" in meta[12560098]["label"], meta[12560098]["label"]
    # spot values (DISCOVERY.md / SOURCES.yaml, verified 2026-10-22)
    assert pt[0][0].startswith("1993-07"), pt[0]
    assert at(pt, "2012-01") == 13.85, at(pt, "2012-01")
    assert len(pt) >= 399, len(pt)
    pt_avg, de_avg = annual_mean(pt), annual_mean(de)
    # The Eurostat Maastricht yield is a different average of a related
    # benchmark; agreement within half a point says we read the right
    # series (2012: 10.55 there), not that they are one number.
    assert abs(pt_avg[2012] - 10.55) < 0.6, pt_avg[2012]
    spread = {y: pt_avg[y] - de_avg[y] for y in pt_avg if y in de_avg}
    write("markets/yield_10y_from_bpstat.csv",
          ["BPstat 12099464 (PT 10y OT, fixed rate, monthly average %) and",
           "12560098 (Germany 10y). Annual mean of COMPLETE years only;",
           "the running year is blank. spread_pp = PT avg - DE avg, computed",
           "here. Beside yield_10y_from_estat.csv (Maastricht criterion",
           "yield) - related, not identical; never spliced."],
          ["yield_pt_avg", "yield_de_avg", "spread_pp"],
          [pt_avg, de_avg, spread], ["{:.2f}"] * 3)
    print(f"     PT Jan-2012 {at(pt, '2012-01')}; 2012 avg {pt_avg[2012]:.2f};"
          f" spread 2012 {spread[2012]:.2f}pp")


def mortgage() -> None:
    obs = observations([12533735, 12710779])
    long_, pct = obs[12533735], obs[12710779]
    assert long_[0][0].startswith("2003-01"), long_[0]
    assert at(long_, "2003-01") == 4.4, at(long_, "2003-01")
    assert at(long_, "2026-08") == 3.0, at(long_, "2026-08")
    assert pct[0][0].startswith("2018-12"), pct[0]
    assert at(pct, "2026-08") == 3.23, at(pct, "2026-08")
    write("markets/mortgage_rate_from_bpstat.csv",
          ["BPstat 12533735: rate on NEW housing loans to households",
           "(long compilation, Jan-2003+); 12710779: percentile-based",
           "new-business rate on VARIABLE-rate housing loans (Dec-2018+).",
           "Two compilations in two columns - never spliced. The",
           "new-business compilation changed over the window; annotate, do",
           "not smooth. Annual mean of complete years; running year blank."],
          ["mortgage_new_avg", "mortgage_var_pctl_avg"],
          [annual_mean(long_), annual_mean(pct)], ["{:.3f}"] * 2)
    print(f"     Jan-2003 {at(long_, '2003-01')}, Aug-2026 "
          f"{at(long_, '2026-08')} / {at(pct, '2026-08')}")


def household_debt() -> None:
    obs = observations([12457924, 12458135, 12458131])
    tot, hous, cons = obs[12457924], obs[12458135], obs[12458131]
    assert tot[0][0].startswith("2007-12"), tot[0]
    # published to two decimals; the verified figures are rounded to €mn
    assert round(at(tot, "2007-12")) == 156083, at(tot, "2007-12")
    assert round(at(tot, "2026-07")) == 183379, at(tot, "2026-07")
    assert round(at(hous, "2007-12"), 1) == 65.7, at(hous, "2007-12")
    assert round(max(v for _, v in hous), 1) == 70.3, max(hous, key=lambda p: p[1])
    assert round(hous[-1][1], 1) == 37.9, hous[-1]
    t, asof = year_end(tot)
    h, _ = year_end(hous)
    c, _ = year_end(cons)
    assert 2006 not in t, "2006 must stay a hole"
    write("credit/household_debt_from_bpstat.csv",
          ["BPstat domain 18: household indebtedness, STOCKS read at",
           "year-end - never summed. 12457924 total EUR mn (MONTHLY);",
           "12458135 housing loans % GDP and 12458131 consumption & other",
           "% GDP (QUARTERLY, so the running year's ratio lags the EUR mn",
           "by a month or more). as_of = month of the EUR mn reading.",
           "Series start Dec-2007: 2006 is a hole, not a zero."],
          ["debt_eur_mn", "housing_pct_gdp", "consumption_other_pct_gdp",
           "as_of"],
          [t, h, c, asof], ["{:.0f}", "{:.1f}", "{:.1f}", "{}"])
    peak = max(hous, key=lambda p: p[1])
    print(f"     Dec-2007 {at(tot, '2007-12'):.0f} mn; housing %GDP "
          f"{at(hous, '2007-12')} -> peak {peak[1]} ({peak[0][:7]}) -> "
          f"{hous[-1][1]} ({hous[-1][0][:7]})")


def npl() -> None:
    obs = observations([12504544])[12504544]
    assert obs[0][0].startswith("2015-12"), obs[0]
    # published unrounded (17.476711); verified figures are to 1 dp
    assert round(at(obs, "2015-12"), 1) == 17.5, at(obs, "2015-12")
    peak = max(obs, key=lambda p: p[1])
    assert round(peak[1], 1) == 17.9 and peak[0].startswith("2016-06"), peak
    assert round(at(obs, "2026-06"), 1) == 2.1, at(obs, "2026-06")
    # quarterly: no year may carry more than four readings
    assert all(len(v) <= 4 for v in by_year(obs).values())
    v, asof = year_end(obs)
    write("credit/npl_from_bpstat.csv",
          ["BPstat 12504544: banking-sector non-performing loans ratio, %,",
           "FSI compilation, QUARTERLY stock ratio read at Q4 (latest",
           "quarter for the running year, see as_of) - never summed or",
           "averaged. Starts 2015Q4; the older BSI-domain 'credito",
           "malparado' definitions are not spliced on. Peak 2016Q2."],
          ["npl_ratio", "as_of"], [v, asof], ["{:.1f}", "{}"])
    print(f"     2015Q4 {obs[0][1]}; peak {peak[1]} ({peak[0][:7]}); "
          f"latest {obs[-1][1]} ({obs[-1][0][:7]})")


BUDGET = {  # column -> series
    "state_revenue_mn": 88873, "state_expenditure_mn": 88884,
    "state_balance_mn": 88894, "state_vat_mn": 88877,
    "state_irs_mn": 88899, "state_irc_mn": 88900,
    "state_interest_mn": 88910,
    "gg_revenue_mn": 12560947, "gg_expenditure_mn": 12560959,
    "gg_balance_mn": 12560943, "gg_interest_mn": 12560989,
}


def budget() -> None:
    obs = observations(list(BUDGET.values()))
    meta = metadata(list(BUDGET.values()))
    for sid in BUDGET.values():
        m = meta[sid]
        assert m["domain_ids"] == [10], (sid, m["domain_ids"])
        lab = cube_labels(10, m["dataset_id"], sid)
        # cash basis, year-to-date, public-accounts criteria - asserted
        # from the cube's own labels, not assumed
        assert lab["Valuation method"] == "Cash value", (sid, lab)
        assert lab["Metrics"] == "Year to date values", (sid, lab)
        assert lab["Criteria"] == "Public accounts criteria", (sid, lab)
        assert lab["Unit of measure"] == "Millions of euros", (sid, lab)
    cols, asof = [], None
    for name, sid in BUDGET.items():
        v, a = year_end(obs[sid])
        cols.append(v)
        if name == "state_balance_mn":
            asof = a
    # YTD sanity: within a year the cumulative revenue never falls by
    # more than a rounding/reclassification hair (a monthly-flow series
    # would fall every January-to-February often; YTD climbs).
    rev = by_year(obs[88873])
    for y, o in rev.items():
        o = sorted(o)
        if len(o) == 12:
            assert o[-1][1] > o[0][1] * 5, (y, o[0], o[-1])
    # identity: balance = revenue - expenditure (December readings)
    st = dict(zip(BUDGET, cols))
    for y in range(Y0, Y1 + 1):
        for p in ("state", "gg"):
            r, e, b = (st[f"{p}_revenue_mn"].get(y),
                       st[f"{p}_expenditure_mn"].get(y),
                       st[f"{p}_balance_mn"].get(y))
            if None not in (r, e, b):
                assert abs(r - e - b) <= max(2.0, abs(b) * 0.01), (p, y, r, e, b)
    comments = [
        "Budget Outturn (Execucao Orcamental), BPstat domain 10, source of",
        "record DGO. CASH basis, public-accounts criteria, EUR mn - the",
        "NATIONAL layer, a different number from the EDP (accrual)",
        "deficit in deficit_from_estat.csv; two files, never spliced.",
        "Series are YEAR-TO-DATE: each year is its December reading, the",
        "running year its latest month (as_of) - never summed. State =",
        "88873/88884/88894 (+VAT 88877, IRS 88899, IRC 88900, interest",
        "88910); general government = 12560947/12560959/12560943",
        "(+interest 12560989); the general-government series start in",
        "2013, so 2006-2012 gg_* cells are holes, not zeros."]
    assert any("cash basis" in c.lower() for c in comments)
    gg_first = min(cols[list(BUDGET).index("gg_balance_mn")])
    assert gg_first == 2013, gg_first   # the comment says so
    cols.append(asof)
    write("fiscal/budget_outturn_from_bpstat.csv", comments,
          list(BUDGET) + ["as_of"], cols, ["{:.1f}"] * len(BUDGET) + ["{}"])
    text = (DATA / "fiscal/budget_outturn_from_bpstat.csv").read_text()
    assert "CASH basis" in text and "YEAR-TO-DATE" in text
    print(f"     State balance {Y1 - 1}: {st['state_balance_mn'][Y1 - 1]:.1f}"
          f" mn; GG balance {Y1 - 1}: {st['gg_balance_mn'][Y1 - 1]:.1f} mn;"
          f" running year as_of {asof[Y1]}")


def maastricht_crosscheck() -> None:
    """Domain 28 GG Maastricht debt % GDP vs the Eurostat sidecar.

    Printed and asserted only; no file. The Eurostat file is the shipped
    Maastricht series - this proves the two publishers agree.
    """
    m = metadata([12561512])[12561512]
    assert m["domain_ids"] == [28] and "% of GDP" in m["label"], m
    bp, _ = year_end(observations([12561512])[12561512])
    estat = DATA / "fiscal/debt_from_estat.csv"
    if not estat.exists():
        print("     (debt_from_estat.csv absent - cross-check skipped)")
        return
    rows = [ln.split(",") for ln in estat.read_text().splitlines()
            if ln and not ln.startswith("#")]
    col = rows[0].index("gross_pct_gdp")
    es = {int(r[0]): float(r[col]) for r in rows[1:] if r[col]}
    common = sorted(set(bp) & set(es))
    assert len(common) >= 15, common
    worst = max(common, key=lambda y: abs(bp[y] - es[y]))
    assert abs(bp[worst] - es[worst]) <= 0.5, (worst, bp[worst], es[worst])
    print(f"     Maastricht 12561512 vs Eurostat: {len(common)} years, "
          f"max gap {abs(bp[worst] - es[worst]):.2f}pp ({worst})")


def main() -> None:
    print("Fetching Banco de Portugal (BPstat) series...")
    yields()
    mortgage()
    household_debt()
    npl()
    budget()
    maastricht_crosscheck()
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
