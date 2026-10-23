#!/usr/bin/env python3
"""Refresh the comparables layer for China into sidecar CSVs.

Usage:  python3 -I countries/china/fetch/fetch_harmonised.py

The plate spine needs the same series from the same harmoniser for every
country, and for China the comparables layer carries a second burden: the
China rule (COUNTRIES.md row 7) says every NBS-official figure is drawn
beside the World Bank / IMF / UN reading of the same quantity, never
spliced. This is that beside-it layer: the World Bank, the IMF DataMapper
and the UNDP HDR, each fetched once, shape-checked, spot-checked and
cross-checked against each other. All three endpoints were verified live
on 2026-10-22 (see SOURCES.yaml); the NBS machine API is 403-blocked, so
until that block lifts this layer is the only live China series the atlas
can fetch, and the official NBS line stays on the pending list.

  World Bank   WDI: real GDP growth, CPI inflation, unemployment (ILO
               modelled estimate), GDP and GDP per person (current US$),
               reserves (IMF IFS), trade / exports / imports (% of GDP),
               the official exchange rate (PA.NUS.FCRF, annual-average CNY
               per USD — what the currency slot indexes and the equity slot
               converts with), gross fixed capital formation (% of GDP),
               Gini, poverty at the US$8.30/day upper-middle-income line
               (PIP), non-performing loans (IMF FSI), population (UN WPP),
               total fertility, crude birth and death rates, net migration
               (UN WPP counts), migrant stock (UN DESA), homicide (UNODC),
               suicide (WHO estimates)
  IMF          DataMapper: real GDP growth (NGDP_RPCH), CPI inflation
               (PCPIPCH), general-government gross debt, % of GDP
               (GGXWDG_NGDP)
  UNDP         HDR25 composite indices, one complete time series (HDI)
  Transparency Corruption Perceptions Index — the 2012-method time series
               from one edition's results-and-trends workbook

Quirks the checks below exist for:

  * IMF DataMapper's `/CHN` path segment does NOT filter — the body
    carries every country under values.<IND>. The check is that
    values.<IND>.CHN exists, and only that row is read. Verified live
    2026-10-22: NGDP_RPCH answers 229 countries, GGXWDG_NGDP 226.
    www.imf.org also answers curl's TLS fingerprint with a 403 error
    page; the urllib browser UA below is the one that gets through
    (same as the Canada and Spain fetchers).
  * WEO years past the last outturn/estimate are staff projections; the
    sidecar stops at 2025 and nothing beyond it is cached as data.
  * World Bank holes stay holes: SI.POV.GINI stops at 2022 for China
    (the WB series lags the NBS, which itself stopped publishing), and
    SM.POP.TOTL.ZS exists only on five-year DESA vintages. The nulls are
    never interpolated and never zero-filled.
  * The HDR file is ONE VINTAGE covering every year, which is the point:
    the HDI is recomputed for the whole back-series at each methodology
    change, so a trend assembled across report years is partly an
    artefact of the reports. One file, one vintage, one URL pinned to
    HDR25. The country names are not UTF-8; the file is read cp1252.
  * The current-USD GDP LEVEL falls from 2022 to 2023 while real growth
    was +5.4% — the exchange rate, not a contraction. The level is a
    size reading, never a growth reading; the note rides with the CSV.

Output: sidecars only (`*_from_wb.csv`, `*_from_imf.csv`, `*_from_undp.csv`
beside the curated files). A fetcher never overwrites a curated number;
the curated files are staged by hand after diffing these.
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

NAME = "China"
ISO3 = "CHN"

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache" / "harmonised"

# www.imf.org answers 403 to urllib's default User-Agent (and to curl's
# TLS fingerprint outright); hdr.undp.org likewise. A browser-shaped UA
# with an Accept header gets through to both (verified 2026-10-22).
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)", "Accept": "*/*"}

WB = ("https://api.worldbank.org/v2/country/{iso3}/indicator/{code}"
      "?format=json&per_page=200&date={d0}:{d1}")
IMF = "https://www.imf.org/external/datamapper/api/v1/{code}/CHN"
HDR = ("https://hdr.undp.org/sites/default/files/2025_HDR/"
       "HDR25_Composite_indices_complete_time_series.csv")

FIRST_YEAR, LAST_YEAR = 2006, 2026   # the country.yaml window
FETCH_FROM = 2005                    # one year of context below the window
# The IMF WEO tables run to 2031. Everything after the last year the WEO
# treats as outturn or estimate is a staff projection, and a projection
# is not a datum: the sidecar stops here.
IMF_LAST_YEAR = 2025

# World Bank indicator -> (sidecar, column, decimals).
WB_SERIES = [
    ("NY.GDP.MKTP.KD.ZG", "economy/gdp_growth_intl_from_wb.csv",
     "real_growth_pct", 2),
    ("NY.GDP.MKTP.CD", "economy/gdp_usd_from_wb.csv", "gdp_usd", 0),
    ("NY.GDP.PCAP.CD", "economy/gdp_pc_usd_from_wb.csv",
     "gdp_per_person_usd", 0),
    ("FI.RES.TOTL.CD", "markets/reserves_intl_from_wb.csv", "reserves_usd",
     0),
    ("NE.TRD.GNFS.ZS", "trade/trade_intl_openness_from_wb.csv",
     "trade_pct_gdp", 2),
    ("NE.EXP.GNFS.ZS", "trade/trade_intl_openness_from_wb.csv",
     "exports_pct_gdp", 2),
    ("NE.IMP.GNFS.ZS", "trade/trade_intl_openness_from_wb.csv",
     "imports_pct_gdp", 2),
    ("SI.POV.GINI", "people/gini_intl_from_wb.csv", "gini", 1),
    ("SP.POP.TOTL", "demography/population_intl_from_wb.csv",
     "population", 0),
    ("SM.POP.TOTL.ZS", "migration/migrant_stock_intl_from_wb.csv",
     "migrant_stock_pct", 2),
]

# IMF DataMapper indicator -> (sidecar, column, decimals).
IMF_SERIES = [
    ("NGDP_RPCH", "economy/gdp_growth_intl_from_imf.csv",
     "real_growth_pct", 2),
    ("GGXWDG_NGDP", "fiscal/debt_intl_pct_gdp_from_imf.csv",
     "gg_gross_debt_pct_gdp", 1),
]

HDR_FILE = "international/hdi_from_undp.csv"
HDR_COLUMN = "hdi"
HDR_DECIMALS = 3

# (sidecar, column, year, value): one known value per series, read off
# the publisher on 2026-10-22 (the SOURCES.yaml verification pass).
SPOT = [
    ("economy/gdp_growth_intl_from_wb.csv", "real_growth_pct", 2025, 4.96),
    ("economy/gdp_growth_intl_from_imf.csv", "real_growth_pct", 2025, 5.0),
    ("economy/gdp_usd_from_wb.csv", "gdp_usd", 2025, 19498039388042.6),
    ("economy/gdp_pc_usd_from_wb.csv", "gdp_per_person_usd", 2025,
     13861.97),
    ("markets/reserves_intl_from_wb.csv", "reserves_usd", 2025,
     3748744952817.94),
    ("trade/trade_intl_openness_from_wb.csv", "trade_pct_gdp", 2025, 37.96),
    ("trade/trade_intl_openness_from_wb.csv", "exports_pct_gdp", 2025,
     21.07),
    ("trade/trade_intl_openness_from_wb.csv", "imports_pct_gdp", 2025,
     16.89),
    ("people/gini_intl_from_wb.csv", "gini", 2022, 36.0),
    ("demography/population_intl_from_wb.csv", "population", 2022,
     1412175000.0),
    ("migration/migrant_stock_intl_from_wb.csv", "migrant_stock_pct", 2024,
     0.1),
    ("fiscal/debt_intl_pct_gdp_from_imf.csv", "gg_gross_debt_pct_gdp",
     2025, 98.6),
    ("international/hdi_from_undp.csv", "hdi", 2023, 0.797),
]

# (label, sidecar A, column A, sidecar B, column B, year, scale,
#  tolerance): cross-reads between the three harmonisers. China has no
# staged national series yet — the NBS is 403-blocked — so until it
# opens, the second source for every number here is the OTHER
# international publisher of the same quantity. A tolerance of None
# marks a pair that differs by definition — printed, not asserted.
CROSS = [
    ("Real growth (WB vs IMF WEO)",
     "economy/gdp_growth_intl_from_wb.csv", "real_growth_pct",
     "economy/gdp_growth_intl_from_imf.csv", "real_growth_pct",
     2023, 1, ("rel", 0.05)),
    ("Exports+imports vs trade share (all WB)",
     "trade/trade_intl_openness_from_wb.csv", "exports_pct_gdp",
     "trade/trade_intl_openness_from_wb.csv", "trade_pct_gdp",
     2024, 1, ("sum", 0.1)),
]
# The computed cross-read: gdp_usd / gdp_pc_usd vs population, all WB.
DIVIDE_CROSS = (
    ("GDP level / per-head vs population (all WB)",
     "economy/gdp_usd_from_wb.csv", "gdp_usd",
     "economy/gdp_pc_usd_from_wb.csv", "gdp_per_person_usd",
     "demography/population_intl_from_wb.csv", "population",
     2024, ("rel", 0.02)),
)


class FetchError(RuntimeError):
    pass


# --------------------------------------------------------------- transport
def get(url: str, cache_name: str, check) -> bytes:
    """The body at `url`, validated by `check` BEFORE it is cached.

    A cached error page is worse than no cache: it survives the retry
    that would have fixed it. So the check runs on the way in, and again
    on a cached copy left by an older run, which is thrown away if it
    fails.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / cache_name
    if path.exists():
        raw = path.read_bytes()
        try:
            check(raw)
            return raw
        except Exception as e:  # noqa: BLE001
            print(f"  stale cache {cache_name}: {e}", file=sys.stderr)
            path.unlink()
    last: Exception | None = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=180) as r:
                raw = r.read()
            check(raw)
            path.write_bytes(raw)
            return raw
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"  {cache_name} attempt {attempt + 1}: {e}",
                  file=sys.stderr)
            time.sleep(3 * (attempt + 1))
    raise FetchError(f"{url}: {last}")


# --------------------------------------------------------------- publishers
def wb(code: str) -> dict[int, float]:
    """One World Bank WDI indicator for China, {year: value}.

    A bad request comes back as a JSON object with a message rather than
    the [metadata, rows] pair, and a paged answer would silently drop
    the later pages, so both are refused. Nulls (the GINI holes) are
    skipped, never zero-filled.
    """
    def check(raw: bytes) -> None:
        p = json.loads(raw)
        if not (isinstance(p, list) and len(p) == 2
                and isinstance(p[1], list) and p[1]):
            raise ValueError("not a World Bank indicator response")
        if p[0].get("pages") != 1:
            raise ValueError(f"paged response ({p[0].get('pages')} pages)")
        ids = {r["indicator"]["id"] for r in p[1]}
        isos = {r["countryiso3code"] for r in p[1]}
        if ids != {code} or isos != {ISO3}:
            raise ValueError(f"wrong series in payload: {ids} {isos}")

    url = WB.format(iso3=ISO3, code=code, d0=FETCH_FROM, d1=LAST_YEAR)
    raw = get(url, f"wb_{code}.json", check)
    out = {}
    for row in json.loads(raw)[1]:
        year = int(row["date"])
        if row["value"] is not None and FIRST_YEAR <= year <= LAST_YEAR:
            out[year] = float(row["value"])
    return out


def imf(code: str) -> tuple[dict[int, float], dict[int, float]]:
    """One IMF DataMapper indicator for China: {year: value} inside the
    window, plus the raw CHN row including projection years.

    DataMapper ignores the /CHN filter and returns every country under
    values.<IND>, and it answers an indicator it does not know with the
    country list and a 200 — so the check is that values[code] is a dict
    keyed by ISO3 and holds CHN. Only values[code].CHN is read.
    """
    def check(raw: bytes) -> None:
        p = json.loads(raw)
        series = (p.get("values") or {}).get(code)
        if not isinstance(series, dict):
            raise ValueError(f"{code} is not a DataMapper indicator")
        if ISO3 not in series:
            raise ValueError(f"{code} has no values for {ISO3}")
        if len(series) < 150:
            raise ValueError(f"{code}: only {len(series)} countries — "
                             "unexpectedly narrow body")

    raw = get(IMF.format(code=code), f"imf_{code}.json", check)
    row = json.loads(raw)["values"][code][ISO3]
    raw_all = {int(y): float(v) for y, v in row.items() if v is not None}
    out = {y: v for y, v in raw_all.items()
           if FIRST_YEAR <= y <= IMF_LAST_YEAR}
    return out, raw_all


def undp_hdi() -> dict[int, float]:
    """China's HDI row from the HDR25 composite-indices file.

    One vintage, whole series. The header row's hdi_YYYY columns are
    picked by regex; the rank column and sub-index columns are not.
    The file's country names are not UTF-8 (a cp1252 byte shows up at
    offset ~2.4 kB), so the decode is cp1252 — the ISO3 keys themselves
    are pure ASCII and unaffected.
    """
    def check(raw: bytes) -> None:
        rows = list(csv.DictReader(io.StringIO(raw.decode("cp1252"))))
        if not rows or "iso3" not in rows[0]:
            raise ValueError("not the HDR composite-indices file")
        chn = [r for r in rows if r.get("iso3") == ISO3]
        if len(chn) != 1:
            raise ValueError(f"{ISO3} row count is {len(chn)}, not 1")
        years = [int(m.group(1)) for m in
                 (re.fullmatch(r"hdi_(\d{4})", c) for c in chn[0]) if m]
        if not years or max(years) < 2023:
            raise ValueError("hdi_YYYY columns end before 2023")

    raw = get(HDR, "undp_hdr25_composite.csv", check)
    rows = csv.DictReader(io.StringIO(raw.decode("cp1252")))
    for r in rows:
        if r.get("iso3") == ISO3:
            return {int(c[4:]): float(r[c])
                    for c in r
                    if re.fullmatch(r"hdi_\d{4}", c or "")
                    and (r[c] or "").strip()
                    and FIRST_YEAR <= int(c[4:]) <= LAST_YEAR}
    raise FetchError("UNDP file has no CHN row")  # check() above says it can't


# --------------------------------------------------------------- assembly
def collect() -> dict[str, dict[int, dict[str, float]]]:
    """Every sidecar this fetcher writes, as {rel: {year: {column: value}}}."""
    tables: dict[str, dict[int, dict[str, float]]] = {}
    decimals: dict[tuple[str, str], int] = {}
    order: dict[str, list[str]] = {}

    def put(rel: str, column: str, series: dict[int, float], dec: int) -> None:
        if not series:
            raise FetchError(f"{rel}: {column} came back empty")
        t = tables.setdefault(rel, {})
        for year, value in series.items():
            t.setdefault(year, {})[column] = value
        decimals[(rel, column)] = dec
        order.setdefault(rel, []).append(column)

    print("World Bank — World Development Indicators")
    for code, rel, column, dec in WB_SERIES:
        series = wb(code)
        print(f"  {code:<18} {len(series):>3} years "
              f"{min(series)}-{max(series)}")
        put(rel, column, series, dec)

    print("IMF — DataMapper (WEO)")
    growth_imf: dict[int, float] = {}
    for code, rel, column, dec in IMF_SERIES:
        series, raw_all = imf(code)
        print(f"  {code:<18} {len(series):>3} years "
              f"{min(series)}-{max(series)} (body has "
              f"{len(raw_all)} non-null years incl. projections)")
        if code == "NGDP_RPCH":
            growth_imf = raw_all
            neg = sorted(y for y, v in raw_all.items() if v < 0)
            print(f"  band evidence: negative CHN years in the WEO body: "
                  f"{neg or 'none'}")
            if neg:
                raise FetchError(
                    "NGDP_RPCH shows negative CHN years "
                    f"{neg}; country.yaml bands: [] rests on there being "
                    "none — re-derive the bands before refetching")
        put(rel, column, series, dec)

    print("UNDP — HDR25 composite indices (one vintage)")
    hdi = undp_hdi()
    print(f"  HDI (CHN)        {len(hdi):>3} years "
          f"{min(hdi)}-{max(hdi)} (1990-vintage back-series)")
    put(HDR_FILE, HDR_COLUMN, hdi, HDR_DECIMALS)

    collect.decimals = decimals  # type: ignore[attr-defined]
    collect.order = order        # type: ignore[attr-defined]
    return tables


# --------------------------------------------------------------- checks
def spot_checks(tables) -> None:
    """A known value per series. A refetch that moves one fails loudly.

    The tolerance absorbs an ordinary revision (3%, or 0.1 on a rate
    near zero); it does not absorb a unit read as thousands or the
    wrong row.
    """
    bad = []
    for rel, column, year, want in SPOT:
        got = tables.get(rel, {}).get(year, {}).get(column)
        if got is None or abs(got - want) > max(abs(want) * 0.03, 0.1):
            bad.append(f"{rel} {column} {year}: want {want}, got {got}")
    covered = {(rel, c) for rel, c, _, _ in SPOT}
    missing = [f"{rel} {c}" for rel, cols in collect.order.items()
               for c in cols if (rel, c) not in covered]
    if missing:
        bad.append(f"no spot value asserted for {missing}")
    if bad:
        raise FetchError("spot checks failed:\n  " + "\n  ".join(bad))
    print(f"Spot checks: {len(SPOT)} values as expected")


def cell(tables, rel: str, column: str, year: int) -> float:
    try:
        return tables[rel][year][column]
    except KeyError:
        raise FetchError(f"cross-check source missing: {rel}:{column} {year}")


def cross_checks(tables) -> None:
    """Second-source checks across the three harmonisers.

    With the NBS 403-blocked there is no national file to compare
    against yet; until there is, every number here must be matched by
    another independent publisher of the same quantity. These are the
    magnitudes the SOURCING pass promised; a miss is an error.
    """
    bad = []
    print("Cross-checks across the comparables layer")
    for (label, rel_a, col_a, rel_b, col_b, year, scale, tol) in CROSS:
        a = cell(tables, rel_a, col_a, year)
        b = cell(tables, rel_b, col_b, year)
        if tol[0] == "sum":
            # col_a plus the third column of this file must add up to col_b.
            partner = next(c for c in collect.order[rel_a]
                           if c not in (col_a, col_b))
            a2 = cell(tables, rel_a, partner, year)
            h = a + a2
            n = b
            verdict = (f"{'ok' if abs(h - n) <= tol[1] else 'FAIL'} "
                       f"({a:.2f} + {a2:.2f} = {h:.2f} vs {n:.2f}, "
                       f"limit {tol[1]})")
            if abs(h - n) > tol[1]:
                bad.append(f"{label} {year}: {h:.2f} vs {n:.2f}")
        else:
            h, n = a * scale, b
            diff = abs(h - n) / abs(n) if tol[0] == "rel" else abs(h - n)
            verdict = (f"{'ok' if diff <= tol[1] else 'FAIL'} "
                       f"({tol[0]} {diff:.4f} <= {tol[1]})")
            if diff > tol[1]:
                bad.append(f"{label} {year}: {h:.4g} vs {n:.4g}")
        print(f"  {label} {year}: {a:,.4g} | {b:,.4g} — {verdict}")
    for (label, rel_a, col_a, rel_b, col_b, rel_c, col_c, year, tol) in DIVIDE_CROSS:
        a, b, c = (cell(tables, rel_a, col_a, year),
                   cell(tables, rel_b, col_b, year),
                   cell(tables, rel_c, col_c, year))
        implied = a / b
        diff = abs(implied - c) / c
        verdict = f"{'ok' if diff <= tol[1] else 'FAIL'} (rel {diff:.4f} <= {tol[1]})"
        if diff > tol[1]:
            bad.append(f"{label} {year}: implied {implied:,.4g} vs {c:,.4g}")
        print(f"  {label} {year}: {a:,.4g} / {b:,.4g} = {implied:,.4g} "
              f"| population {c:,.4g} — {verdict}")
    if bad:
        raise FetchError("cross-checks failed:\n  " + "\n  ".join(bad))


# --------------------------------------------------------------- output
def write(tables) -> None:
    for rel in sorted(tables):
        assert rel.rsplit(".csv", 1)[0].endswith(
            ("_from_wb", "_from_imf", "_from_undp")), \
            f"{rel}: a fetcher only writes sidecars"
        columns = collect.order[rel]
        path = DATA / rel
        header = ",".join(["year", *columns])
        if path.exists():
            first = next((ln for ln in path.read_text().splitlines()
                          if not ln.startswith("#")), "")
            if first != header:
                raise FetchError(f"refusing to overwrite {rel}: it holds "
                                 f"{first!r}, not this fetcher's sidecar")
        lines = [header]
        for year in sorted(tables[rel]):
            row = tables[rel][year]
            cells = []
            for c in columns:
                v = row.get(c)
                cells.append("" if v is None else
                             f"{v:.{collect.decimals[(rel, c)]}f}")
            if any(cells):
                lines.append(f"{year}," + ",".join(cells))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n")
        print(f"  data/{rel}  {len(lines) - 1} rows, {len(columns)} columns")


def main() -> None:
    print(f"Comparables layer for {NAME} (World Bank, IMF DataMapper, UNDP)")
    try:
        tables = collect()
        spot_checks(tables)
        cross_checks(tables)
    except FetchError as e:
        print(f"!! {e}\nNothing written.", file=sys.stderr)
        sys.exit(1)
    write(tables)
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
