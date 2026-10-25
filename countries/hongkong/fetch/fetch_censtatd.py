"""Census and Statistics Department (C&SD) — the national layer.

    python3 -m countries.hongkong.fetch.fetch_censtatd [--offline]

Writes review sidecars under `data/**/*_from_censtatd.csv` only. It never
touches a curated file (SOURCING_A_COUNTRY.md §6).

The endpoint is the one C&SD documents in its own API list
(`https://www.censtatd.gov.hk/en/api.html`, machine-readable at
`https://www.censtatd.gov.hk/data/WebTableList.json`):

    https://www.censtatd.gov.hk/api/get.php?id=<table>&lang=en&full_series=1

`full_series=1` returns the complete table as JSON with no `param`
selection. That matters: the `param` form the web page uses is an LZ-string
of the reader's UI selection and cannot be reconstructed from documentation,
while `full_series=1` is stable and reproducible.

Traps found in the discovery pass, all of them recorded in DISCOVERY.md:

1. The gateway answers HTTP 403 to Python's default `urllib` User-Agent and
   accepts a plain `curl/8.5.0` one. The UA is set explicitly; a 403 is
   retried and then reported as a failure, never cached.
2. An unknown table id returns `{"header": {"success": false, "err_msg":
   "API not found"}}` under HTTP 200. A valid id with no `param` returns
   `{"header": {"status": {"code": 0}}, "dataSet": []}`. Both parse cleanly;
   an empty `dataSet` is a failure here, not an empty table.
3. Rows leave a key out entirely when it does not apply (total rows omit
   `SEX`; `115-01011` mixes per-sex and total rows in one `sv`). Nothing is
   keyed by position.
4. Provisional, revised and footnote-flagged cells carry `sd_value` of `p`,
   `r` or a footnote marker. The flag travels in the sidecar as `sd_value`
   so a review can see which figures are not yet final.

Every table is pinned to a published observation before its sidecar is
written, so a payload that answers 200 with the wrong table is caught rather
than committed.
"""
from __future__ import annotations

import csv
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "censtatd"
DATA = ROOT / "data"
BASE = "https://www.censtatd.gov.hk/api/get.php?id={id}&lang=en&full_series=1"
UA = "curl/8.5.0"          # see module docstring: urllib's default is 403'd


def pin(period, sv, value, unit=None, d1=None, d2=None, freq="Y"):
    return dict(period=period, sv=sv, value=value, unit=unit,
                d1=d1, d2=d2, freq=freq)


# table id -> sidecar stem, expected title fragment, dimension fields, pins.
# dims are the payload's dimension field names, outermost first.
TABLES: dict[str, dict] = {
    # ---- economy -------------------------------------------------------
    "310-31001": dict(file="macro/gdp", title="Gross Domestic Product",
                      dims=[], pins=[
                          pin("2025", "CUR", 3329843, unit="HK$ million"),
                          pin("2025", "CURPGDP", 444044, unit="HK$"),
                          pin("2020", "CUR", 2675793, unit="HK$ million"),
                      ]),
    "310-30001": dict(file="macro/gdp_growth", title="Percentage change",
                      dims=["GDP_COMPONENT"], pins=[
                          pin("2020", "CON", -6.5, unit="Year-on-year"),
                          pin("2025", "CON", 3.6, unit="Year-on-year"),
                      ]),
    "310-31002": dict(file="macro/gdp_expenditure", title="by major expenditure",
                      dims=["GDP_COMPONENT"], pins=[
                          pin("2025", "CUR", 3329843, unit="HK$ million", d1=""),
                          pin("2025", "CUR", 2205779, unit="HK$ million", d1="PCE"),
                      ]),
    "310-31006": dict(file="macro/gdp_ratios", title="Ratio of major",
                      dims=["GDP_COMPONENT"], pins=[
                          pin("2025", "CUR", 172.9, unit="%", d1="XG"),
                          pin("2025", "CUR", 21.9, unit="%", d1="MS"),
                      ]),
    "310-32031": dict(file="spending/gfcf", title="fixed capital formation",
                      dims=["GDP_COMPONENT"], pins=[
                          pin("2025", "CUR", 563949, unit="HK$ million", d1="GDFCF"),
                      ]),
    "310-32023": dict(file="spending/gce_function", title="social and economic function",
                      dims=["GDP_COMPONENT"], pins=[
                          pin("2025", "CUR", 100, unit="Percentage distribution", d1="GCE"),
                          pin("2025", "CUR", 3.7, unit="Percentage distribution", d1="GCE_social"),
                      ]),
    "510-60001": dict(file="macro/cpi", title="Consumer Price Indices",
                      dims=[], pins=[
                          pin("2024", "CC_CM_1920", 107.3, unit="Index"),
                          pin("2024", "A_CM_1920", 109.5, unit="Index"),
                      ]),
    "510-60002": dict(file="macro/cpi_underlying", title="Underlying Consumer",
                      dims=[], pins=[
                          pin("2024", "UCC_CM_1920", 108.1, unit="Index"),
                      ]),
    "210-06101": dict(file="macro/labour", title="labour force",
                      dims=["SEX"], pins=[
                          pin("2024", "UR", 3.0, unit="%"),
                          pin("2024", "LF", 3807.4, unit="No. ('000)"),
                          pin("2024", "EM", 3693.6, unit="No. ('000)"),
                      ]),
    "130-06102": dict(file="people/household_income",
                      title="Statistics on domestic households",
                      dims=[], pins=[
                          pin("2024", "MED_DH_INC", 30000, unit="HK$"),
                          pin("2024", "DH", 2763.1, unit="No. ('000)"),
                      ]),
    # ---- fiscal --------------------------------------------------------
    # 340-47001 is the General Revenue Account, the government's own cash
    # accounts, keyed by the financial year in which it ends (2024/25 is
    # labelled 2024). Tables 47011/47012 widen the perimeter to include the
    # statutory funds but stop at 2018.
    "340-47001": dict(file="fiscal/govt_gra", title="General Revenue Account",
                      dims=["TYPE_GRA"], pins=[
                          pin("2024", "REV_GRA", 278773, unit="HK$ million", d1="REV_1"),
                          pin("2024", "EXP_GRA", 604834, unit="HK$ million", d1="EXP_1"),
                      ]),
    "340-47011": dict(file="fiscal/govt_revenue", title="Government revenue",
                      dims=["REV_TYPE"], pins=[
                          pin("2018", "GOV_REV", 599774, unit="HK$ million", d1=""),
                      ]),
    "340-47012": dict(file="fiscal/govt_expenditure", title="Government expenditure",
                      dims=["EXP_TYPE"], pins=[
                          pin("2018", "GOV_EXP", 531825, unit="HK$ million", d1=""),
                      ]),
    # ---- trade ---------------------------------------------------------
    "410-50001": dict(file="trade/merchandise", title="merchandise trade aggregate",
                      dims=[], pins=[
                          pin("2025", "VAL_TX", 5240251, unit="HK$ million"),
                          pin("2024", "VAL_IM", 4922101, unit="HK$ million"),
                          pin("2024", "BAL", -379731, unit="HK$ million"),
                      ]),
    "410-50013": dict(file="trade/destinations", title="ten main destinations",
                      dims=["COUNTRY"], pins=[
                          pin("2025", "VAL_TX", 5240251, unit="HK$ million", d1=""),
                          pin("2024", "VAL_TX", 2681658, unit="HK$ million", d1="631"),
                      ]),
    "410-50032": dict(file="trade/products", title="ten principal commodity",
                      dims=["COMMD"], pins=[
                          pin("2025", "VAL_TX", 5240251, unit="HK$ million", d1=""),
                          pin("2024", "VAL_TX", 2182692, unit="HK$ million", d1="77"),
                      ]),
    "420-57001": dict(file="trade/services", title="Exports and imports of services",
                      dims=["EBOPS"], pins=[
                          pin("2023", "XS", 759991, unit="HK$ million"),
                          pin("2023", "MS", 618375, unit="HK$ million"),
                      ]),
    # ---- markets -------------------------------------------------------
    "340-46001": dict(file="markets/fx", title="Exchange rates",
                      dims=[], pins=[
                          pin("2024", "FC_USD", 7.803, unit="HK dollar per unit"),
                          pin("2020", "FC_USD", 7.757, unit="HK dollar per unit"),
                      ]),
    "340-45021": dict(file="markets/interest_rates", title="interest rates",
                      dims=["DEP_P_T"], pins=[
                          pin("2024", "BL_RATE", 5.77, unit="Percent"),
                          pin("2020", "BL_RATE", 5.0, unit="Percent"),
                      ]),
    "340-45022": dict(file="markets/hibor", title="Interest Settlement Rates",
                      dims=["MATURITY"], pins=[
                          pin("2024", "SET_RATE", 5.65, unit="Rates at end",
                              d1="0N"),
                          pin("2024", "SET_RATE", 4.58, unit="Rates at end",
                              d1="1M"),
                      ]),
    "340-46002": dict(file="markets/twi", title="Effective exchange rate",
                      dims=[], pins=[
                          pin("2024", "EERI_T", 105.4, unit="Index"),
                          pin("2020", "EERI_T", 100.0, unit="Index"),
                      ]),
    # ---- demography ----------------------------------------------------
    "110-01001": dict(file="demography/population", title="Population by sex and age",
                      dims=["SEX", "AGE"], pins=[
                          pin("202512", "POP", 7508.7, unit="Number ('000)", d1="", d2="", freq="H"),
                          pin("202406", "POP", 7524.1, unit="Number ('000)", d1="", d2="", freq="H"),
                      ]),
    "110-01004": dict(file="demography/dependency", title="Dependency ratio",
                      dims=["SEX"], pins=[
                          pin("2025", "TDEPR", 499, unit="Ratio"),
                          pin("2025", "MED_AGE_POPN", 48.4, unit="(years)"),
                      ]),
    "110-01003": dict(file="demography/components", title="Population growth by component",
                      dims=["TYPE_INFLOW"], pins=[
                          pin("202512", "PG", 8.1, unit="('000)", freq="H"),
                          pin("202512", "NM", 27.1, unit="('000)", d1="", freq="H"),
                          pin("202512", "NC", -18.9, unit="('000)", freq="H"),
                      ]),
    "115-01011": dict(file="demography/vital", title="Vital events",
                      dims=["SEX"], pins=[
                          pin("2024", "CDR", 7.0, unit="Rate", d1=""),
                          pin("2024", "CBR", 4.9, unit="Rate", d1=""),
                          pin("2024", "TFR_XFDH", 841, unit="Rate", d1=""),
                          pin("2024", "ELB_M", 88.2, unit="(years)", d1="F"),
                      ]),
    "115-01016": dict(file="demography/fertility", title="Age specific fertility",
                      dims=["AGE"], pins=[
                          pin("2024", "ASFR", 68.1, unit="Rate", d1="30-34"),
                          pin("2024", "ASFR", 25.5, unit="Rate", d1=""),
                      ]),
    "115-01021": dict(file="demography/life_tables", title="life tables",
                      dims=["SEX", "AGE"], pins=[
                          pin("2024", "EX", 87.31, unit="e(x)", d1="F", d2=1),
                          pin("2024", "EX", 81.88, unit="e(x)", d1="M", d2=1),
                      ]),
    # ---- security ------------------------------------------------------
    "940-92033": dict(file="security/cases", title="Cases reported",
                      dims=["OFF"], pins=[
                          pin("2024", "PP_CASE_RPT", 94747, unit="Number", d1=""),
                          pin("2024", "PP_CASE_RPT", 19, unit="Number", d1=103),
                      ]),
    "940-92031": dict(file="security/arrests", title="Persons arrested",
                      dims=["OFF", "AGE", "HKPF_REGION", "SEX"], pins=[
                          pin("2024", "PP_CRIME", 36269, unit="Number"),
                      ]),
}


class FetchError(SystemExit):
    pass


def fail(msg: str) -> None:
    print(f"fetch_censtatd: {msg}", file=sys.stderr)
    sys.exit(1)


def payload(table: str, offline: bool) -> dict:
    cache_file = CACHE / f"{table}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))
    if offline:
        fail(f"offline and no cached payload for {table} ({cache_file})")
    url = BASE.format(id=table)
    body = ctype = None
    for attempt in (1, 2, 3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                ctype = r.headers.get("Content-Type", "")
                body = r.read()
            break
        except urllib.error.HTTPError as e:
            if e.code in (403, 429, 503) and attempt < 3:
                time.sleep(5 * attempt)      # WAF; back off, do not cache
                continue
            fail(f"{table}: HTTP {e.code} from {url}")
        except urllib.error.URLError as e:
            fail(f"{table}: {e.reason} from {url}")
    if body is None:                          # pragma: no cover
        fail(f"{table}: no payload after retries")
    if "json" not in ctype.lower() and not body.lstrip().startswith(b"{"):
        fail(f"{table}: HTTP 200 but Content-Type {ctype!r} — not JSON")
    try:
        doc = json.loads(body)
    except json.JSONDecodeError:
        fail(f"{table}: HTTP 200 body is not JSON ({body[:80]!r})")
    if "dataSet" not in doc:
        fail(f"{table}: no dataSet key — endpoint said "
             f"{doc.get('header', {}).get('err_msg', 'nothing')}")
    CACHE.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(body.decode("utf-8"), encoding="utf-8")
    return doc


def cell(value) -> str:
    """A figure as a CSV cell. Empty means the publisher left it out."""
    if value is None or value == "":
        return ""
    if isinstance(value, bool):
        raise FetchError(f"unexpected boolean cell {value!r}")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value == int(value) and abs(value) < 1e15:
            return str(int(value))
        return repr(value)
    return str(value).strip()


def matches(row: dict, spec: dict, dims: list[str]) -> bool:
    if row.get("freq") != spec["freq"] or row.get("period") != spec["period"]:
        return False
    if row.get("sv") != spec["sv"]:
        return False
    if spec["unit"] and spec["unit"] not in str(row.get("svDesc", "")):
        return False
    for i, key in enumerate(("d1", "d2")):
        want = spec[key]
        if want is None or i >= len(dims):
            continue
        if str(row.get(dims[i], "")).strip() != str(want):
            return False
    return True


def main(argv: list[str]) -> None:
    offline = "--offline" in argv
    for table, spec in TABLES.items():
        doc = payload(table, offline)
        title = doc["header"].get("title", "")
        if spec["title"].lower() not in title.lower():
            fail(f"{table}: title {title!r} does not contain "
                 f"{spec['title']!r} — wrong table answered")
        rows = doc["dataSet"]
        if not rows:
            fail(f"{table}: dataSet is empty (the empty-param trap)")
        dims = spec["dims"]
        for d in dims:
            if d not in rows[0] and not any(d in r for r in rows):
                fail(f"{table}: expected dimension {d!r}; payload has "
                     f"{sorted(rows[0])}")
        for p in spec["pins"]:
            found = [r for r in rows if matches(r, p, dims)]
            if not found:
                fail(f"{table}: pinned row {p} is absent")
            got = found[0].get("figure")
            if not isinstance(got, (int, float)) or abs(got - p["value"]) > 0.051:
                fail(f"{table}: pinned {p['period']} {p['sv']} = {got!r}, "
                     f"expected {p['value']}")

        out = DATA / f"{spec['file']}_from_censtatd.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        # The footnote flag is a column only when the table actually uses it:
        # an all-empty column is a column of nothing, and the data tests say so.
        has_flag = any(str(r.get("sd_value", "")).strip() for r in rows)
        header = (["freq", "period", "series", "unit"]
                  + [f"dim{i + 1}_{k}" for i in range(len(dims))
                     for k in ("code", "desc")]
                  + ["value"] + (["flag"] if has_flag else []))
        lines = []
        for r in rows:
            rec = [str(r.get("freq", "")), str(r.get("period", "")),
                   str(r.get("sv", "")), str(r.get("svDesc", ""))]
            for d in dims:
                rec += [str(r.get(d, "")), str(r.get(f"{d}Desc", ""))]
            rec.append(cell(r.get("figure")))
            if has_flag:
                rec.append(str(r.get("sd_value", "")).strip())
            lines.append(rec)
        lines.sort(key=lambda x: (x[2], x[0], x[1])
                   + tuple(x[4 + 2 * i] for i in range(len(dims))))
        with out.open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(header)
            w.writerows(lines)
        print(f"  {table:>10} {title[:50]:<50} -> {out.relative_to(ROOT)} "
              f"({len(lines)} rows)")


if __name__ == "__main__":
    main(sys.argv[1:])
