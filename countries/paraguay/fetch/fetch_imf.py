#!/usr/bin/env python3
"""Refresh Paraguay's IMF series into sidecar CSVs.

Usage:  make C=paraguay fetch   (or: python3 -I fetch/fetch_imf.py)

Two IMF routes, both probed live on 2026-10-25:

  DataMapper (WEO, October 2026 vintage)
      NGDP_RPCH      real GDP growth, %
      rev, exp       general government revenue / expenditure, % of GDP
      GGXCNL_NGDP    overall balance, % of GDP
      pb             primary balance, % of GDP
      ie             interest paid, % of GDP
      GGXWDG_NGDP    gross debt, % of GDP

  SDMX 2.1 (api.imf.org), the member's own reported series as the IMF
  redistributes them — this is the only route to the Banco Central del
  Paraguay's numbers that answers from this network, because bcp.gov.py
  serves a Cloudflare challenge on every path:
      CPI  PRY.CPI._T.YOY_PCH_PA_PT.A   CPI, all items, year on year, %
      ER   PRY.USD_XDC.PA_RT.A          US$ per guarani, period average
                                        (staged reciprocated, PYG per US$)

The WEO is a *staff* vintage: observed years go in the plain column and
everything after the country's last full year goes in a `_proj` column,
so a forecast can never be drawn as an outturn. The SDMX series are
observed only and carry no projection.

Nothing here is spliced with a national series. The BCP's own releases
are `meta.pending` in SOURCES.yaml, not silently replaced.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"

ISO3 = "PRY"
DATAMAPPER = "https://www.imf.org/external/datamapper/api/v1/{code}/{iso3}"
SDMX = ("https://api.imf.org/external/sdmx/2.1/data/IMF.STA,{flow}/{key}"
        "?startPeriod={start}")

# www.imf.org's edge answers 403 to any UA starting with "Mozilla/5.0"
# (verified in the UK lane 2026-10-22); a plain descriptive UA gets 200
# from both hosts.
HEADERS = {"User-Agent": "worldreports-data-fetcher/1.0"}

YEAR_FROM, YEAR_TO = 2006, 2026
LAST_FULL_YEAR = 2025

# WEO indicators: (code, column, decimals). Observed <= LAST_FULL_YEAR,
# projections in `<column>_proj`.
WEO_FISCAL = [
    ("rev", "revenue_pct_gdp", 2),
    ("exp", "expenditure_pct_gdp", 2),
    ("GGXCNL_NGDP", "balance_pct_gdp", 2),
    ("pb", "primary_balance_pct_gdp", 2),
    ("ie", "interest_pct_gdp", 2),
    ("GGXWDG_NGDP", "debt_pct_gdp", 2),
]
WEO_GROWTH = ("NGDP_RPCH", "gdp_growth_pct", 2)

COMMENTS = {
    "macro/growth_from_imf.csv": [
        "IMF WEO (October 2026 vintage) NGDP_RPCH: real GDP growth, %.",
        "Observed years in the plain column; WEO staff projections only in",
        "gdp_growth_pct_proj. The independent agreement line for the World",
        "Bank series (2024: 4.7 on both; 2022: 0.0 vs -0.02).",
    ],
    "macro/cpi_from_imf.csv": [
        "IMF SDMX CPI, PRY.CPI._T.YOY_PCH_PA_PT: all items, year on year,",
        "percent. This is the BCP's consumer price index as the IMF records",
        "it — the BCP computes Paraguay's CPI, not the INE, and bcp.gov.py",
        "answers a Cloudflare challenge from this network. Identical to the",
        "World Bank's FP.CPI.TOTL.ZG to two decimals (2006: 9.59 on both).",
    ],
    "markets/fx_from_imf.csv": [
        "IMF SDMX ER, PRY.USD_XDC.PA_RT: US$ per guarani, period average,",
        "staged reciprocated as guaranies per US$. 2006 = 5,635.09;",
        "2025 = 7,545.3. Same convention as the World Bank's PA.NUS.FCRF.",
    ],
    "trade/partners_from_imf.csv": [
        "IMF DOTS (IMTS dataflow), Paraguay's customs returns as the Fund",
        "redistributes them: exports of goods FOB, US$, by partner, annual.",
        "Shares are of the world total the same payload carries (G001),",
        "never of the partners shown. Four largest destinations in 2024 plus",
        "the rest, so the five columns sum to 100 in every year. Cross-",
        "checked once against UN Comtrade: 2024 world total US$10.914bn",
        "there and US$10.916bn here.",
    ],
    "fiscal/fiscal_from_imf.csv": [
        "IMF WEO (October 2026 vintage), general government: rev, exp,",
        "GGXCNL_NGDP, pb, ie, GGXWDG_NGDP, all in % of GDP. One vintage for",
        "every column. WEO revenue and expenditure stop at 2024 (Paraguay",
        "does not report them further in this vintage), so 2025 is blank in",
        "those two columns; the balance and debt carry 2025 and projections",
        "to 2031 only in the _proj columns. This is the general-government",
        "accrual perimeter, NOT the MEF's central-administration cash",
        "presentation in fiscal/fiscal_national.csv.",
    ],
}


def cached(url: str, name: str, validate) -> bytes:
    """Fetch once into cache/, validating the payload before it is kept.

    An error page cached is worse than no cache: it survives the retry
    that would have fixed it. `validate` raises on a wrong shape.
    """
    CACHE.mkdir(exist_ok=True)
    path = CACHE / name
    if path.exists():
        return path.read_bytes()
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=120) as r:
                raw = r.read()
            validate(raw)
            path.write_bytes(raw)
            return raw
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"  {name} attempt {attempt + 1}: {e}", file=sys.stderr)
            time.sleep(3 * (attempt + 1))
    raise SystemExit(f"cannot fetch {url}: {last}")


def datamapper(code: str) -> dict[int, float]:
    url = DATAMAPPER.format(code=code, iso3=ISO3)

    def validate(raw: bytes) -> None:
        payload = json.loads(raw)
        values = payload.get("values", {}).get(code, {}).get(ISO3)
        if not isinstance(values, dict) or not values:
            raise ValueError("not a DataMapper indicator response")

    payload = json.loads(cached(url, f"imf_weo_{code}.json", validate))
    values = payload["values"][code][ISO3]
    return {int(y): float(v) for y, v in values.items() if v is not None}


def _validate_sdmx(raw: bytes) -> None:
    text = raw.decode("utf-8", "replace")
    if "<Series " not in text:
        raise ValueError("no series in the SDMX payload")
    if "OBS_VALUE" not in text:
        raise ValueError("no observations in the SDMX payload")


def sdmx(flow: str, key: str, name: str) -> dict[int, float]:
    url = SDMX.format(flow=flow, key=key, start=YEAR_FROM)
    text = cached(url, name, _validate_sdmx).decode("utf-8")
    out: dict[int, float] = {}
    for series in re.finditer(r"<Series [^>]*>(.*?)</Series>", text, re.S):
        for year, value in re.findall(
                r'TIME_PERIOD="(\d{4})" OBS_VALUE="([^"]+)"',
                series.group(1)):
            out[int(year)] = float(value)
    return out


def write(rel: str, columns: list[tuple[str, dict[int, float], int]]) -> None:
    empty = [c for c, s, _ in columns if not s]
    if empty:
        raise SystemExit(f"{rel}: {empty} came back empty, nothing written")
    path = ROOT / "data" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {c}" for c in COMMENTS.get(rel, [])]
    lines.append("year," + ",".join(c for c, _, _ in columns))
    years = sorted(set().union(*(s for _, s, _ in columns)))
    rows = 0
    for y in years:
        if not YEAR_FROM <= y <= YEAR_TO:
            continue
        cells = [f"{series[y]:.{dec}f}" if y in series else ""
                 for _, series, dec in columns]
        lines.append(f"{y}," + ",".join(cells))
        rows += 1
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  data/{rel}  {rows} rows")


def write_weo(rel: str, specs, comments_key: str) -> None:
    """Observed years in one set of columns, WEO forecasts in `_proj`.

    A `_proj` column is written only for an indicator that actually
    carries years past the last full year: a column that is empty in
    every row is a promise the data do not keep (and test_data says so).
    """
    series = {code: datamapper(code) for code, _, _ in specs}
    path = ROOT / "data" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    projected_specs = [s for s in specs
                       if any(y > LAST_FULL_YEAR for y in series[s[0]])]
    cols = [c for _, c, _ in specs]
    proj_cols = [c for _, c, _ in projected_specs]
    lines = [f"# {c}" for c in COMMENTS[comments_key]]
    lines.append("year," + ",".join(cols + [f"{c}_proj" for c in proj_cols]))
    years = sorted(set().union(*series.values()))
    rows = 0
    for y in years:
        if not YEAR_FROM <= y <= YEAR_TO:
            continue
        observed, projected = [], []
        by_col = {}
        for code, column, dec in specs:
            s = series[code]
            value = s[y] if (y <= LAST_FULL_YEAR and y in s) else None
            by_col[column] = value
            observed.append("" if value is None else f"{value:.{dec}f}")
        for code, column, dec in projected_specs:
            s = series[code]
            if y <= LAST_FULL_YEAR:
                projected.append("")
                continue
            value = s[y] if y in s else None
            projected.append("" if value is None else f"{value:.{dec}f}")
        lines.append(f"{y}," + ",".join(observed + projected))
        rows += 1
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  data/{rel}  {rows} rows (observed <= {LAST_FULL_YEAR})")


def verify(weo: dict[str, dict[int, float]], cpi: dict[int, float],
           fx_usd_per_pyg: dict[int, float]) -> None:
    """Pin what the discovery pass checked live on 2026-10-25."""
    growth = weo[WEO_GROWTH[0]]
    assert abs(growth[2024] - 4.7) < 0.05, f"WEO growth 2024: {growth.get(2024)}"
    assert abs(growth[2023] - 5.3) < 0.05, f"WEO growth 2023: {growth.get(2023)}"
    fiscal = {c: weo[c] for c, _, _ in WEO_FISCAL}
    assert abs(fiscal["rev"][2024] - 18.9) < 0.05, \
        f"WEO revenue 2024: {fiscal['rev'].get(2024)}"
    assert abs(fiscal["exp"][2024] - 21.0) < 0.05, \
        f"WEO expenditure 2024: {fiscal['exp'].get(2024)}"
    assert abs(fiscal["GGXCNL_NGDP"][2024] - -2.1) < 0.05, \
        f"WEO balance 2024: {fiscal['GGXCNL_NGDP'].get(2024)}"
    assert abs(fiscal["GGXWDG_NGDP"][2024] - 44.6) < 0.05, \
        f"WEO debt 2024: {fiscal['GGXWDG_NGDP'].get(2024)}"
    # The balance must be revenue minus expenditure, or the six columns
    # are not one consistent presentation.
    for y in (2019, 2022, 2024):
        gap = fiscal["rev"][y] - fiscal["exp"][y] - fiscal["GGXCNL_NGDP"][y]
        assert abs(gap) < 0.11, f"WEO fiscal identity {y}: {gap:.2f}"
    assert abs(cpi[2022] - 9.766) < 0.01, f"IMF CPI 2022: {cpi.get(2022)}"
    assert abs(1 / fx_usd_per_pyg[2006] - 5635.09) < 1.0, \
        f"IMF FX 2006: {1 / fx_usd_per_pyg.get(2006)}"


def _imts_observations(raw: bytes) -> list[tuple[str, float]]:
    """(counterpart code, value) for every series that carries an observation.

    Parsed as XML, not with a regex over `<Series ...>(.*?)</Series>`. A
    self-closing `<Series .../>` — a partner the Fund reports as a series
    with no observation that year — does not end in `</Series>`, so such a
    regex pairs it with the NEXT series' closing tag and hands the empty
    partner the following partner's value. That is not hypothetical: it
    zeroed Argentina's share for 2016-2020 in the first curated file and
    inflated the rest-of-world residual by the same amount, because the
    empty series that preceded ARG in those payloads swallowed ARG's
    observation. Every year is now parsed by structure, and the promoted
    file pins ARG 2016 at 10.18%.
    """
    root = ET.fromstring(raw)
    out: list[tuple[str, float]] = []
    for series in root.iter():
        if not series.tag.endswith("Series"):
            continue
        code = series.get("COUNTERPART_COUNTRY")
        if code is None:
            continue
        for obs in series:
            if obs.tag.endswith("Obs") and obs.get("OBS_VALUE") is not None:
                out.append((code, float(obs.get("OBS_VALUE"))))
                break
    return out


def partners() -> None:
    """Export destinations as shares of total goods exports, 2006-2025.

    IMF DOTS (IMTS dataflow), Paraguay's own customs returns as the Fund
    redistributes them: COUNTRY=PRY, INDICATOR=XG_FOB_USD,
    COUNTERPART_COUNTRY=<partner>, annual. G001 is the world total the
    same payload carries; the shares are computed against it, never
    against a sum of the shown partners (which would force the shares to
    100 by construction). Cross-checked once against UN Comtrade: the
    2024 world total is US$10.914bn there and US$10.916bn here.

    The four partners are the largest in the latest year; every other
    destination is aggregated into `rest_pct`, so the five columns sum to
    100 in every year.
    """
    years = range(YEAR_FROM, LAST_FULL_YEAR + 1)
    rows: dict[int, dict[str, float]] = {}
    for y in years:
        url = SDMX.format(flow="IMTS", key="PRY.XG_FOB_USD..A",
                          start=y).replace(f"startPeriod={y}",
                                           f"startPeriod={y}&endPeriod={y}")
        raw = cached(url, f"imf_imts_{y}.xml", _validate_sdmx)
        values: dict[str, float] = {}
        total = None
        for code, obs in _imts_observations(raw):
            if code == "G001":
                total = obs
            elif not code.startswith("G"):
                values[code] = obs
        if not total:
            raise SystemExit(f"IMTS {y}: no world total (G001)")
        rows[y] = {k: 100.0 * v / total for k, v in values.items()}
    top = ["ARG", "BRA", "CHL", "USA"]
    path = ROOT / "data" / "trade" / "partners_from_imf.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    names = ["argentina_pct", "brazil_pct", "chile_pct", "usa_pct", "rest_pct"]
    lines = [f"# {c}" for c in COMMENTS["trade/partners_from_imf.csv"]]
    lines.append("year," + ",".join(names))
    for y in sorted(rows):
        # A named partner the Fund did not report that year stays blank.
        # `dict.get(p, 0.0)` is how Argentina came to read 0.00% for five
        # years: a missing observation is not a trade flow of zero, and the
        # rest-of-world residual must not absorb it either.
        if any(p not in rows[y] for p in top):
            lines.append(f"{y}," + ",".join([""] * len(names)))
            continue
        shares = [rows[y][p] for p in top]
        rest = 100.0 - sum(shares)
        lines.append(f"{y}," + ",".join(f"{v:.2f}" for v in shares + [rest]))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  data/trade/partners_from_imf.csv  {len(rows)} rows")
    assert abs(rows[2024]["ARG"] - 33.1) < 0.2, rows[2024].get("ARG")
    assert abs(rows[2006]["BRA"] - 47.6) < 0.2, rows[2006].get("BRA")
    # The Argentina series is the one the self-closing-series bug ate: the
    # 2016 payload carries US$887.8m of US$8.72bn, 10.18% of the total.
    assert abs(rows[2016]["ARG"] - 10.18) < 0.02, rows[2016].get("ARG")


def main() -> None:
    print("IMF series for Paraguay")
    weo = {code: datamapper(code) for code, _, _ in WEO_FISCAL}
    weo[WEO_GROWTH[0]] = datamapper(WEO_GROWTH[0])
    write_weo("fiscal/fiscal_from_imf.csv", WEO_FISCAL,
              "fiscal/fiscal_from_imf.csv")
    write_weo("macro/growth_from_imf.csv", [WEO_GROWTH],
              "macro/growth_from_imf.csv")
    cpi = sdmx("CPI", "PRY.CPI._T.YOY_PCH_PA_PT.A", "imf_cpi_yoy.xml")
    write("macro/cpi_from_imf.csv", [("cpi_inflation_pct", cpi, 2)])
    fx = sdmx("ER", "PRY.USD_XDC.PA_RT.A", "imf_er_usd_xdc.xml")
    pyg = {y: 1.0 / v for y, v in fx.items() if v}
    write("markets/fx_from_imf.csv", [("pyg_per_usd", pyg, 2)])
    verify(weo, cpi, fx)
    partners()
    print("All discovery anchors verified.")
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
