#!/usr/bin/env python3
"""Fetch the five harmonised spine series missing from the research pass."""
from __future__ import annotations

import csv
import io
import json
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "worldreports-data-fetcher/1.0"}
WB = ("https://api.worldbank.org/v2/country/CHE/indicator/{code}"
      "?format=json&per_page=100&date=2006:2026")
BIS = ("https://stats.bis.org/api/v2/data/dataflow/BIS/WS_TC/2.0/"
       "Q.CH.H.A.M.770.A?format=csv")
ESTAT = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/"
         "data/gov_10a_main?geo=CH&freq=A&na_item=P51G&sector=S13&unit=PC_GDP")


def get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                               timeout=120) as response:
        return response.read()


def wb(code: str) -> list[tuple[int, float]]:
    payload = json.loads(get(WB.format(code=code)))
    if not (isinstance(payload, list) and len(payload) == 2):
        raise ValueError(f"World Bank {code}: response changed shape")
    return sorted((int(row["date"]), float(row["value"]))
                  for row in payload[1] if row.get("value") is not None)


def bis() -> list[tuple[int, str, str, int]]:
    rows = csv.DictReader(io.StringIO(get(BIS).decode("utf-8-sig")))
    grouped: dict[int, list[tuple[int, float]]] = defaultdict(list)
    for row in rows:
        year, quarter = row["TIME_PERIOD"].split("-Q")
        if 2006 <= int(year) <= 2026:
            grouped[int(year)].append((int(quarter), float(row["OBS_VALUE"])))
    out = []
    for year, values in sorted(grouped.items()):
        q4 = next((v for q, v in values if q == 4), None)
        out.append((year, "" if q4 is None else f"{q4:.1f}",
                    f"{sum(v for _, v in values) / len(values):.1f}",
                    len(values)))
    assert dict((y, q4) for y, q4, _, _ in out)[2025] == "122.9"
    return out


def estat_gfcf() -> list[tuple[int, float]]:
    payload = json.loads(get(ESTAT))
    times = payload["dimension"]["time"]["category"]["index"]
    values = payload["value"]
    out = sorted((int(year), float(values[str(pos)]))
                 for year, pos in times.items() if str(pos) in values
                 and 2006 <= int(year) <= 2026)
    assert abs(dict(out)[2024] - 3.1) < 0.01
    return out


def write_csv(rel: str, header: list[str], rows) -> None:
    path = ROOT / "data" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def main() -> None:
    write_csv("credit/household_credit_from_bis.csv",
              ["year", "household_credit_pct_gdp_q4",
               "household_credit_pct_gdp_qavg", "quarters"], bis())
    for rel, code, column in (
        ("credit/npl_from_wb.csv", "FB.AST.NPER.ZS", "npl_pct"),
        ("security/homicide_from_wb.csv", "VC.IHR.PSRC.P5", "homicide_per_100k"),
        ("security/road_deaths_from_wb.csv", "SH.STA.TRAF.P5", "road_deaths_per_100k"),
        ("social/poverty_from_wb.csv", "SI.POV.UMIC", "poverty_8_30_pct"),
    ):
        write_csv(rel, ["year", column],
                  ((year, f"{value:.2f}") for year, value in wb(code)))
    write_csv("fiscal/public_investment_from_estat.csv",
              ["year", "public_investment_pct_gdp"],
              ((year, f"{value:.1f}") for year, value in estat_gfcf()))


if __name__ == "__main__":
    main()
