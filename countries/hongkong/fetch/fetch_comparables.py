"""The harmonised comparison layer for Hong Kong.

    python3 -m countries.hongkong.fetch.fetch_comparables [--offline]

Three publishers, three endpoints, one script because each is a handful of
series and each writes a sidecar nobody edits by hand:

    World Bank  https://api.worldbank.org/v2/country/HKG/indicator/<code>
    IMF         https://www.imf.org/external/datamapper/api/v1/<indicator>/HKG
    UNDP        HDR composite-indices complete time series (one CSV)

The IMF reports Hong Kong as an SAR economy — `HKG` in DataMapper, with
`rev`, `exp`, `pb`, `GGXWDG_NGDP` and `ie` covering the general government.
That is the only general-government perimeter published for Hong Kong; the
government's own accounts (C&SD 340-47001) are the General Revenue Account,
a cash account on the government's own perimeter. The two are never spliced.

The World Bank carries `HKG` in WDI for national accounts, trade, reserves
and population. It does NOT carry Gini, national poverty, suicide or road
deaths for Hong Kong — those indicator calls answer with an empty data
array, which this script reports rather than writes.
"""
from __future__ import annotations

import csv
import io
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"
DATA = ROOT / "data"

WB = ("https://api.worldbank.org/v2/country/HKG/indicator/{code}"
      "?format=json&per_page=200&date=1990:2026")
IMF = "https://www.imf.org/external/datamapper/api/v1/{code}/HKG"
HDR = ("https://hdr.undp.org/sites/default/files/2025_HDR/"
       "HDR25_Composite_indices_complete_time_series.csv")
ISO3 = "HKG"
# User-Agent per host, and both facts are load-bearing: hdr.undp.org answers
# 403 to urllib's default string, and imf.org answers 403 to a browser
# string while accepting a plain curl one (probed 2026-10-25, DISCOVERY.md).
UA_BROWSER = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
UA_CURL = {"User-Agent": "curl/8.5.0"}

# (indicator, sidecar stem, column, decimals)
WB_WANTED = [
    ("NY.GDP.MKTP.CD", "world/gdp_usd", "gdp_usd", 0),
    ("NY.GDP.PCAP.CD", "world/gdp_per_person_usd", "gdp_per_person_usd", 0),
    ("FI.RES.TOTL.CD", "world/reserves_usd", "reserves_usd", 0),
    ("SP.POP.TOTL", "demography/population_wb", "population", 0),
    ("SP.DYN.TFRT.IN", "demography/fertility_wb", "tfr", 3),
    ("SP.DYN.LE00.IN", "demography/life_expectancy_wb", "life_expectancy", 2),
    ("SP.DYN.CBRT.IN", "demography/birth_rate_wb", "birth_rate", 3),
    ("SP.DYN.CDRT.IN", "demography/death_rate_wb", "death_rate", 3),
    ("SM.POP.NETM", "migration/net_migration_wb", "net_migration", 0),
    ("VC.IHR.PSRC.P5", "security/homicide_wb", "homicide_per_100k", 3),
    ("NE.EXP.GNFS.ZS", "trade/exports_pct_gdp_wb", "exports_pct_gdp", 2),
    ("NE.IMP.GNFS.ZS", "trade/imports_pct_gdp_wb", "imports_pct_gdp", 2),
    ("NE.GDI.FTOT.ZS", "spending/gfcf_pct_gdp_wb", "gfcf_pct_gdp", 2),
    ("SL.UEM.TOTL.ZS", "macro/unemployment_wb", "unemployment", 2),
    ("NY.GDP.MKTP.KD.ZG", "macro/growth_wb", "real_growth", 2),
    ("FP.CPI.TOTL.ZG", "macro/inflation_wb", "inflation", 3),
]

IMF_WANTED = [
    ("rev", "fiscal/imf_revenue", "revenue_pct_gdp"),
    ("exp", "fiscal/imf_expenditure", "expenditure_pct_gdp"),
    ("pb", "fiscal/imf_primary_balance", "primary_balance_pct_gdp"),
    ("GGXWDG_NGDP", "fiscal/imf_gross_debt", "gross_debt_pct_gdp"),
    ("ie", "fiscal/imf_interest", "interest_pct_gdp"),
    ("NGDP_RPCH", "macro/imf_growth", "real_growth"),
    ("PCPIPCH", "macro/imf_inflation", "inflation"),
    ("LUR", "macro/imf_unemployment", "unemployment"),
    ("NGDPD", "world/imf_gdp_usd", "gdp_usd"),
    ("NGDPDPC", "world/imf_gdp_per_person_usd", "gdp_per_person_usd"),
]

# Observations the payloads are pinned to before any sidecar is written.
WB_PINS = {
    "NY.GDP.MKTP.CD": {2024: 406_865_000_000},
    "NY.GDP.PCAP.CD": {2024: 54_100},
    "VC.IHR.PSRC.P5": {2022: 0.4},
    "FI.RES.TOTL.CD": {2023: 425_554_111_033},
}
IMF_PINS = {
    "rev": {2024: 17.45},
    "exp": {2024: 23.26},
    "GGXWDG_NGDP": {2024: 9.2},
}


class FetchError(SystemExit):
    pass


def fail(msg: str) -> None:
    print(f"fetch_comparables: {msg}", file=sys.stderr)
    sys.exit(1)


def get(url: str, cache_name: str, offline: bool,
        headers: dict | None = None) -> bytes:
    cache_file = CACHE / cache_name
    if cache_file.exists():
        return cache_file.read_bytes()
    if offline:
        fail(f"offline and no cached payload {cache_file}")
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=headers or UA_BROWSER)
            with urllib.request.urlopen(req, timeout=120) as r:
                ctype = r.headers.get("Content-Type", "")
                body = r.read()
            if "json" in url and "json" not in ctype.lower():
                raise ValueError(f"Content-Type {ctype!r} is not JSON")
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_bytes(body)
            return body
        except Exception as e:  # noqa: BLE001 — network, shape, HTTP
            last = e
            time.sleep(3 * (attempt + 1))
    fail(f"{url}: {last}")


def wb_series(code: str, offline: bool) -> dict[int, float]:
    body = get(WB.format(code=code), f"wb_{code}.json", offline, UA_CURL)
    payload = json.loads(body)
    if not (isinstance(payload, list) and len(payload) > 1
            and isinstance(payload[1], list)):
        fail(f"World Bank {code}: not an indicator response ({str(payload)[:120]})")
    out = {int(r["date"]): float(r["value"])
           for r in payload[1] if r.get("value") is not None}
    for year, want in WB_PINS.get(code, {}).items():
        got = out.get(year)
        if got is None or abs(got - want) > max(1.0, abs(want) * 0.02):
            fail(f"World Bank {code}: {year} = {got!r}, expected ~{want}")
    return out


def imf_series(code: str, offline: bool) -> dict[int, float]:
    body = get(IMF.format(code=code), f"imf_{code}.json", offline, UA_CURL)
    doc = json.loads(body)
    series = (doc.get("values") or {}).get(code)
    if not series or "HKG" not in series:
        fail(f"IMF {code}: no HKG series ({list(doc)[:5]})")
    out = {int(y): float(v) for y, v in series["HKG"].items()
           if v is not None and str(y).isdigit()}
    for year, want in IMF_PINS.get(code, {}).items():
        got = out.get(year)
        if got is None or abs(got - want) > max(1.0, abs(want) * 0.15):
            fail(f"IMF {code}: {year} = {got!r}, expected ~{want}")
    return out


def hdr_hdi(offline: bool) -> dict[int, float]:
    body = get(HDR, "hdr25_series.csv", offline, UA_BROWSER)
    out: dict[int, float] = {}
    for row in csv.DictReader(io.StringIO(body.decode("utf-8", "replace"))):
        iso = (row.get("iso3") or row.get("ISO3") or "").strip()
        if iso != ISO3:
            continue
        for key, value in row.items():
            if not key or value in (None, "", ".."):
                continue
            name = key.lower()
            year = name.rsplit("_", 1)[-1]
            if year.isdigit() and name == f"hdi_{year}":
                out[int(year)] = float(value)
        break
    if not out:
        fail("HDR: no HKG row — the UNDP file does not carry this economy")
    return out


def write(stem: str, source: str, column: str, series: dict[int, float],
          decimals: int) -> None:
    if not series:
        fail(f"{stem}: empty series from {source}, nothing written")
    out = DATA / f"{stem}_from_{source}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ["year," + column]
    for year in sorted(series):
        value = series[year]
        cell = (str(int(round(value))) if decimals == 0
                else f"{value:.{decimals}f}")
        lines.append(f"{year},{cell}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  {out.relative_to(ROOT)}  ({len(series)} years, "
          f"{min(series)}-{max(series)})")


def main(argv: list[str]) -> None:
    offline = "--offline" in argv
    for code, stem, column, decimals in WB_WANTED:
        write(stem, "wb", column, wb_series(code, offline), decimals)
    for code, stem, column in IMF_WANTED:
        out = DATA / f"{stem}_from_imf.csv"
        series = imf_series(code, offline)
        out.parent.mkdir(parents=True, exist_ok=True)
        lines = ["year," + column]
        lines += [f"{y},{series[y]:.4f}".rstrip("0").rstrip(".")
                  for y in sorted(series)]
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"  {out.relative_to(ROOT)}  ({len(series)} years, "
              f"{min(series)}-{max(series)})")
    hdi = hdr_hdi(offline)
    out = DATA / "world/hdi_from_undp.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ["year,hdi"] + [f"{y},{hdi[y]:.3f}" for y in sorted(hdi)]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  {out.relative_to(ROOT)}  ({len(hdi)} years, "
          f"{min(hdi)}-{max(hdi)})")


if __name__ == "__main__":
    main(sys.argv[1:])
