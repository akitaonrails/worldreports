#!/usr/bin/env python3
"""Fetch general-government interest payable from the IMF GFS API."""
from __future__ import annotations

import csv
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
URL = ("https://api.imf.org/external/sdmx/2.1/data/IMF.STA,GFS_SOO/"
       "GBR.S13....A?startPeriod=2005")


def main() -> None:
    req = urllib.request.Request(
        URL, headers={"User-Agent": "worldreports-data-fetcher/1.0"})
    with urllib.request.urlopen(req, timeout=180) as response:
        root = ET.fromstring(response.read())
    matches = [series for series in root.iter()
               if series.tag.endswith("Series")
               and series.attrib.get("COUNTRY") == "GBR"
               and series.attrib.get("SECTOR") == "S13"
               and series.attrib.get("INDICATOR") == "G24_T"
               and series.attrib.get("TYPE_OF_TRANSFORMATION") == "POGDP_PT"
               and series.attrib.get("FREQUENCY") == "A"]
    if len(matches) != 1:
        raise ValueError(f"expected one exact GFS series, got {len(matches)}")
    rows = [(int(obs.attrib["TIME_PERIOD"]), float(obs.attrib["OBS_VALUE"]))
            for obs in matches[0] if obs.tag.endswith("Obs")
            and obs.attrib.get("OBS_VALUE")]
    values = dict(rows)
    assert abs(values[2006] - 2.081) < 0.001
    assert abs(values[2022] - 4.363) < 0.001
    assert abs(values[2024] - 2.970) < 0.001
    path = ROOT / "data" / "fiscal" / "gfs_operations_from_imf.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(["year", "interest_payable_pct_gdp"])
        writer.writerows((year, f"{value:.3f}") for year, value in rows
                         if 2006 <= year <= 2026)
    print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
