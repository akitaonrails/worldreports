#!/usr/bin/env python3
"""Fetch UK goods trade by partner from HMRC's uktradeinfo OData API.

Usage:  make C=united-kingdom fetch   (or: python3 countries/united-kingdom/fetch/fetch_uktradeinfo.py)

HMRC publishes Overseas Trade Statistics through an OData v4 API at
api.uktradeinfo.com — no key, and it answers a filtered aggregate in
seconds where the ONS beta API did not answer at all. These are CUSTOMS
VALUE, GOODS ONLY figures and are never spliced with the ONS
balance-of-payments series in `data/trade/trade_totals_from_ons.csv`
(the manifest keeps the two separate; for the USA the two bases differed
by ~$300bn, and for the UK the 2024 US-export total differs by ~3% —
see the magnitude assertion below).

Conventions pinned live on 2026-10-22 before anything was written:

  * The OTS entity set is granular: one row per
    month × flow × commodity × country × port, ~505,000 rows for a
    single month at full granularity, so nothing raw is ever pulled —
    every query is a server-side `$apply` groupby/aggregate.
  * FlowTypeId 1/2 = EU imports/exports, 3/4 = non-EU imports/exports,
    and the id follows the PARTNER'S bloc, not the reporting regime:
    Germany still reads 1/2 in 2024, after Brexit. Imports = 1+3,
    exports = 2+4.
  * The -990-class sentinels are NOT totals. CommodityId=-990 and
    PortId=-1 appear only on unallocated "Estimates" rows
    (CountryId 959, the below-threshold Intrastat bucket); there is no
    all-commodities or all-ports row for a named country. The
    suspicious 2.0 cell from the discovery probe was a genuine tiny
    port-level shipment line, which is exactly why partner totals are
    computed by aggregation, never read off one row.
  * Special CountryIds (951/952 stores & provisions, 958 low-value
    non-EU, 959 estimates, 962 low-value EU, 977 confidential country)
    are included in HMRC's published world totals but carry no partner,
    so they are in the world total and out of every partner series.
    SuppressionIndex 2/3 rows (≈0.5% of value) still carry their value
    and are part of the published totals.

  * The United States has TWO CountryIds: 902 ("USA") carries
    2006-01..2008-12 and 400 ("United States") carries 2009-01 onward,
    with no overlap (verified live 2026-10-22). Filtering on 400 alone
    silently drops 2006–2008; the partner is the sum of both ids, and
    a month present under both would fail the run. No other partner
    drawn here has a second id on the codelist.

Magnitude assertions, made before anything is written. The published
anchors are PARSED from the publisher pages at run time (cached under
cache/uktradeinfo/), never typed in; both numbers are printed so the
reader can see the gap, not just the check:

  * HMRC's December 2025 commentary: total goods exports / imports for
    December 2025, and December 2024 recovered from the commentary's own
    "down/up by £X billion compared with December 2024" lines. Computed
    world totals for both months asserted within 5% (provisional
    vintages move).
    https://www.uktradeinfo.com/trade-data/overseas/2025/uk-overseas-trade-in-goods-statistics-december-2025
  * ONS "UK trade with the United States: 2024": exports of goods to the
    US and the US share of all goods imports. The ONS figure is the
    balance-of-payments basis, a different quantity by construction, so
    exports are asserted within 8% (catches a wrong-flow/wrong-id error,
    leaves room for the basis gap); the import share within 0.5 pp.
    https://www.ons.gov.uk/economy/nationalaccounts/balanceofpayments/articles/uktradewiththeunitedstates/2024

Outputs:
  data/trade/goods_by_partner_from_uktradeinfo.csv
      year,country,imports,exports,balance,import_share,months
      values in £ billion; import_share is of the customs world total,
      special buckets included, as above.
"""
from __future__ import annotations

import csv
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache" / "uktradeinfo"

BASE = "https://api.uktradeinfo.com/OTS"
CODELIST = "https://api.uktradeinfo.com/Country"

Y0, Y1 = 2006, 2026
CHUNK = 3  # years per query — a wider window errors server-side ("An error
           # has occurred" under HTTP 200) on a full-history request

# The partners the plate draws: the name written out, then every HMRC
# CountryId that carries it with the codelist name each id must have.
# The id map is asserted against the live Country codelist before use —
# 400 = United States is the convention the whole file hangs on, and 902
# is the pre-2009 id for the same partner (module docstring).
PARTNERS = (
    ("United States", {400: "United States", 902: "USA"}),
    ("Germany", {4: "Germany"}),
    ("China", {720: "China"}),
    ("Netherlands", {3: "Netherlands"}),
    ("France", {1: "France"}),
    ("Ireland", {7: "Ireland"}),
    ("Switzerland", {39: "Switzerland"}),
    ("Belgium", {17: "Belgium"}),
    ("Italy", {5: "Italy"}),
    ("Spain", {11: "Spain"}),
)

IMPORT_FLOWS = (1, 3)   # EU, then non-EU
EXPORT_FLOWS = (2, 4)

# Publisher pages the magnitude anchors are parsed from (module docstring).
HMRC_DEC_2025 = ("https://www.uktradeinfo.com/trade-data/overseas/2025/"
                 "uk-overseas-trade-in-goods-statistics-december-2025")
ONS_US_2024 = ("https://www.ons.gov.uk/economy/nationalaccounts/"
               "balanceofpayments/articles/uktradewiththeunitedstates/2024")


def aggregate(apply: str, cache_name: str) -> list[dict]:
    """One server-side aggregate query, cached as JSON.

    The API has two failure disguises: a plain-text rate-limit rejection
    under HTTP 200, and a {"error": ...} object for a query it refuses
    (a window that is too wide). Both fail the shape check, and nothing
    is cached that is not a page of aggregate rows — a cached error page
    is worse than no cache, because it survives the retry that would
    have fixed it.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE / f"{cache_name}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())["value"]
    url = BASE + "?$apply=" + urllib.parse.quote(apply, safe="(),=")
    last = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                text = r.read().decode("utf-8-sig")
            payload = json.loads(text)
            if not isinstance(payload.get("value"), list):
                raise ValueError(f"not an aggregate response: {text[:200]!r}")
            cache_file.write_text(text)
            time.sleep(1.0)  # the API rate-limits rapid fire
            return payload["value"]
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"  {cache_name} attempt {attempt + 1}: {e}",
                  file=sys.stderr)
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"uktradeinfo {cache_name}: {last}")


def page_text(url: str, cache_name: str) -> str:
    """A publisher page as flat text (tags stripped), cached as HTML."""
    CACHE.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE / f"{cache_name}.html"
    if cache_file.exists():
        raw = cache_file.read_text(encoding="utf-8")
    else:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read().decode("utf-8", errors="replace")
        if "billion" not in raw:
            raise RuntimeError(f"{url}: no figures on the page — wall or redesign")
        cache_file.write_text(raw, encoding="utf-8")
        time.sleep(1.0)
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    return re.sub(r"\s+", " ", text)


def grab(pattern: str, text: str, what: str) -> re.Match:
    m = re.search(pattern, text)
    if not m:
        raise SystemExit(f"published anchor not found ({what}): /{pattern}/ — "
                         f"the page moved; re-pin before writing anything")
    return m


def hmrc_anchors() -> dict[tuple[int, str], float]:
    """{(MonthId, flow): £} for Dec 2025 and Dec 2024 from HMRC's commentary."""
    text = page_text(HMRC_DEC_2025, "hmrc_commentary_2025_12")
    out = {}
    for flow in ("exports", "imports"):
        m = grab(rf"total goods {flow} were £([\d.]+) billion : "
                 rf".*? (up|down) by £([\d.]+) billion or [\d.]+% compared "
                 rf"with December 2024", text, f"HMRC Dec-2025 {flow}")
        now, sign, delta = float(m[1]), m[2], float(m[3])
        out[(202512, flow)] = now * 1e9
        out[(202412, flow)] = (now - delta if sign == "up" else now + delta) * 1e9
    return out


def ons_us_anchors() -> tuple[float, float]:
    """(US goods exports 2024 £, US share of all goods imports 2024 %)."""
    text = page_text(ONS_US_2024, "ons_us_trade_2024")
    m = grab(r"In 2024, the UK imported £[\d.]+ billion of goods from the "
             r"United States \(([\d.]+)% of all goods imports\) and exported "
             r"£([\d.]+) billion of goods", text, "ONS US 2024")
    return float(m[2]) * 1e9, float(m[1])


def months_grouped(year_from: int, year_to: int, country_id: int | None,
                   cache_prefix: str, allow_empty: bool = False) -> list[dict]:
    """Value by (MonthId, FlowTypeId), in CHUNK-year slices.

    One request over the whole history errors server-side, so the window
    is sliced; each slice is ~70 rows of aggregate, never raw data.
    """
    rows = []
    start = year_from
    while start <= year_to:
        end = min(start + CHUNK - 1, year_to)
        where = f"MonthId ge {start}01 and MonthId le {end}12"
        if country_id is not None:
            where += f" and CountryId eq {country_id}"
        got = aggregate(
            f"filter({where})/groupby((MonthId,FlowTypeId),"
            f"aggregate(Value with sum as V))",
            f"{cache_prefix}_{start}_{end}")
        if not got and not allow_empty:
            raise SystemExit(f"uktradeinfo {cache_prefix} {start}–{end}: empty "
                             f"aggregate under HTTP 200 — a moved id, not a "
                             f"zero; refusing to write a hole as data")
        rows += got
        start = end + 1
    return rows


def by_year(rows: list[dict]) -> dict[int, dict[str, float]]:
    """{(year): {"imports": £, "exports": £, "months": n}} from month rows."""
    out: dict[int, dict] = defaultdict(
        lambda: {"imports": 0.0, "exports": 0.0, "_months": set()})
    for row in rows:
        if row.get("V") is None:
            continue
        month, flow, value = int(row["MonthId"]), int(row["FlowTypeId"]), float(row["V"])
        year = month // 100
        cell = out[year]
        if flow in IMPORT_FLOWS:
            cell["imports"] += value
        elif flow in EXPORT_FLOWS:
            cell["exports"] += value
        else:
            raise ValueError(f"unknown FlowTypeId {flow}")
        cell["_months"].add(month)
    for cell in out.values():
        cell["months"] = len(cell.pop("_months"))
    return dict(out)


def main() -> None:
    print("HMRC uktradeinfo — goods trade by partner (customs value)")

    codelist_file = CACHE / "country_codelist.json"
    CACHE.mkdir(parents=True, exist_ok=True)
    if codelist_file.exists():
        countries = json.loads(codelist_file.read_text())
    else:
        with urllib.request.urlopen(CODELIST + "?$top=400", timeout=60) as r:
            countries = json.loads(r.read().decode("utf-8-sig"))["value"]
        codelist_file.write_text(json.dumps(countries))
        time.sleep(1.0)
    names = {int(c["CountryId"]): c["CountryName"] for c in countries}
    for partner, ids in PARTNERS:
        for cid, name in ids.items():
            if names.get(cid) != name:
                raise SystemExit(
                    f"CountryId {cid} is {names.get(cid)!r} on the live "
                    f"codelist, not {name!r} ({partner}) — the id conventions "
                    f"have moved, re-pin them before trusting anything below")

    world_rows = months_grouped(Y0, Y1, None, "world")
    world = by_year(world_rows)

    # Magnitude assertions BEFORE any partner fetch or write: if the
    # conventions have drifted, the world totals are where it shows.
    computed = defaultdict(float)
    for r in world_rows:
        flow = "exports" if r["FlowTypeId"] in EXPORT_FLOWS else "imports"
        computed[(int(r["MonthId"]), flow)] += float(r["V"])
    for (month, flow), want in sorted(hmrc_anchors().items()):
        got = computed[(month, flow)]
        print(f"  world {month} {flow}: £{got / 1e9:.2f}bn computed vs "
              f"£{want / 1e9:.1f}bn HMRC (Dec-2025 commentary)")
        if abs(got - want) / want > 0.05:
            raise SystemExit(
                f"world {month} {flow} off by more than 5% — not writing "
                f"anything until the total conventions are re-pinned")

    partners = {}
    for partner, ids in PARTNERS:
        rows = []
        seen: dict[tuple, int] = {}
        for cid in ids:
            got = months_grouped(Y0, Y1, cid, f"partner_{cid}",
                                 allow_empty=len(ids) > 1)
            for r in got:
                key = (r["MonthId"], r["FlowTypeId"])
                if key in seen:
                    raise SystemExit(f"{partner}: {key} under both CountryId "
                                     f"{seen[key]} and {cid} — double count")
                seen[key] = cid
            rows += got
        partners[partner] = by_year(rows)
        # Every year before the current one must be a full twelve months:
        # a short year is a moved id, not a dip.
        for year in range(Y0, Y1):
            months = partners[partner].get(year, {}).get("months", 0)
            if months != 12:
                raise SystemExit(f"{partner} {year}: {months} months — hole")

    us_exp_pub, us_share_pub = ons_us_anchors()
    us24 = partners["United States"][2024]
    us_share = us24["imports"] / world[2024]["imports"] * 100
    print(f"  US 2024 exports: £{us24['exports'] / 1e9:.2f}bn computed (customs) "
          f"vs £{us_exp_pub / 1e9:.1f}bn ONS headline (BoP basis); import "
          f"share {us_share:.2f}% computed vs {us_share_pub}% ONS")
    if abs(us24["exports"] - us_exp_pub) / us_exp_pub > 0.08:
        raise SystemExit("US 2024 exports off by more than 8% — different "
                         "basis but same order of magnitude; not writing")
    if abs(us_share - us_share_pub) > 0.5:
        raise SystemExit("US 2024 import share off by more than 0.5 pp — "
                         "the world denominator is wrong; not writing")

    path = DATA / "trade" / "goods_by_partner_from_uktradeinfo.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["year", "country", "imports", "exports", "balance",
                    "import_share", "months"])
        for year in range(Y0, Y1 + 1):
            world_imp = world.get(year, {}).get("imports")
            for name, _ in PARTNERS:
                cell = partners[name].get(year)
                if not cell or not cell["months"]:
                    continue
                imp, exp = cell["imports"] / 1e9, cell["exports"] / 1e9
                share = (f"{cell['imports'] / world_imp * 100:.2f}"
                         if world_imp else "")  # no denominator → blank, not 0
                w.writerow([year, name, f"{imp:.1f}", f"{exp:.1f}",
                            f"{exp - imp:.1f}", share,
                            cell["months"]])
                n += 1
    print(f"  {path.relative_to(ROOT)}  {n} rows")
    print("Done. Diff the sidecar before adopting.")


if __name__ == "__main__":
    main()
