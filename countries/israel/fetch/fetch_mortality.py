#!/usr/bin/env python3
"""Refresh Israel mortality from OECD Health Statistics into a sidecar.

The source is OECD Causes of Mortality, SDMX flow
``OECD.ELS.HD,DSD_HEALTH_STAT@DF_COM,1.1``. OECD documents the counts as
coming from the WHO Mortality Database, which in turn contains the official
vital-registration records transmitted by national authorities and codes the
underlying cause of death.

Only these observations are staged:

* annual frequency, Israel, both sexes, all ages;
* raw death counts (``DT`` / calculation not applicable); and
* crude rates per 100,000 (``DT_10P5HB`` / ``CRUDE``).

Age-standardised rates exist in the same payload and are deliberately rejected.
The plate's crude all-cause rate is the OECD rate divided by 100 to express it
per 1,000. Excess deaths use the atlas-wide fixed rule: the percentage above
the arithmetic mean of the 2015--2019 all-cause counts, with no population or
age adjustment. Values before 2015 remain blank for that derived column.

The script writes only ``data/mortality/mortality_from_oecd.csv``. Review that
sidecar before promoting it to ``mortality.csv``.
"""
from __future__ import annotations

import csv
import io
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "mortality"
CACHE = ROOT / "cache" / "mortality"

URL = (
    "https://sdmx.oecd.org/public/rest/data/"
    "OECD.ELS.HD,DSD_HEALTH_STAT@DF_COM,1.1/"
    "ISR.A...........?startPeriod=2005&endPeriod=2026"
)
ACCEPT = "application/vnd.sdmx.data+csv;version=1.0.0"

# OECD cause codes used here. _T is all causes; the three named categories
# are direct children of the OECD cause-of-death codelist.
CAUSES = {
    "_T": "all",
    "CICDCVID": "covid",
    "CICDTUME": "malignant_neoplasms",
    "CICDCIRC": "circulatory",
}

# Values read from the same OECD flow in Data Explorer on 2026-10-23.
SPOT = {
    (2021, "deaths_all"): 50_772.0,
    (2021, "covid_deaths"): 4_800.0,
    (2021, "covid_per_100k"): 51.2,
    (2021, "malignant_neoplasms_per_100k"): 123.6,
    (2021, "circulatory_per_100k"): 109.3,
    (2023, "deaths_all"): 49_654.0,
    (2023, "covid_deaths"): 1_028.0,
}


class FetchError(RuntimeError):
    pass


def validate_payload(raw: bytes) -> list[dict[str, str]]:
    if raw.lstrip().startswith((b"<", b"{")):
        raise FetchError("OECD returned HTML/JSON rather than SDMX-CSV")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise FetchError("OECD payload is not UTF-8 CSV") from exc
    rows = list(csv.DictReader(io.StringIO(text)))
    required = {
        "REF_AREA", "FREQ", "MEASURE", "UNIT_MEASURE", "AGE", "SEX",
        "SOCIO_ECON_STATUS", "DEATH_CAUSE", "CALC_METHODOLOGY",
        "GESTATION_THRESHOLD", "HEALTH_STATUS", "DISEASE", "CANCER_SITE",
        "TIME_PERIOD", "OBS_VALUE", "OBS_STATUS",
    }
    if not rows or not required.issubset(rows[0]):
        missing = required - (set(rows[0]) if rows else set())
        raise FetchError(f"OECD schema changed or is empty; missing {sorted(missing)}")
    if len(rows) < 5_000:
        raise FetchError(f"OECD payload unexpectedly short: {len(rows)} rows")
    if {r["REF_AREA"] for r in rows} != {"ISR"}:
        raise FetchError("country filter did not return Israel alone")
    return rows


def get() -> list[dict[str, str]]:
    CACHE.mkdir(parents=True, exist_ok=True)
    cached = CACHE / "oecd_causes_of_mortality.csv"
    if cached.exists():
        try:
            return validate_payload(cached.read_bytes())
        except FetchError as exc:
            print(f"stale mortality cache rejected: {exc}", file=sys.stderr)
            cached.unlink()

    request = urllib.request.Request(
        URL,
        headers={
            "User-Agent": "worldreports.io data refresh",
            "Accept": ACCEPT,
        },
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        raw = response.read()
        content_type = response.headers.get_content_type()
    if content_type not in {"text/csv", "application/vnd.sdmx.data+csv"}:
        raise FetchError(f"unexpected OECD content type: {content_type}")
    rows = validate_payload(raw)
    cached.write_bytes(raw)
    return rows


def selected(rows: list[dict[str, str]]) -> dict[int, dict[str, float]]:
    out: dict[int, dict[str, float]] = {}
    seen: set[tuple[int, str]] = set()
    for row in rows:
        if not (
            row["REF_AREA"] == "ISR"
            and row["FREQ"] == "A"
            and row["MEASURE"] == "CSEM"
            and row["AGE"] == "_T"
            and row["SEX"] == "_T"
            and row["SOCIO_ECON_STATUS"] == "_Z"
            and row["GESTATION_THRESHOLD"] == "_Z"
            and row["HEALTH_STATUS"] == "_Z"
            and row["DISEASE"] == "_Z"
            and row["CANCER_SITE"] == "_Z"
            and row["DEATH_CAUSE"] in CAUSES
            and row["OBS_VALUE"]
        ):
            continue
        if row["OBS_STATUS"]:
            raise FetchError(
                f"flagged observation {row['TIME_PERIOD']} "
                f"{row['DEATH_CAUSE']}: {row['OBS_STATUS']}"
            )

        cause = CAUSES[row["DEATH_CAUSE"]]
        if row["UNIT_MEASURE"] == "DT" and row["CALC_METHODOLOGY"] == "_Z":
            field = f"{cause}_deaths" if cause != "all" else "deaths_all"
        elif (
            row["UNIT_MEASURE"] == "DT_10P5HB"
            and row["CALC_METHODOLOGY"] == "CRUDE"
        ):
            field = f"{cause}_per_100k"
            if cause != "all":
                field = f"{cause}_per_100k"
            else:
                field = "death_rate_per_1000"
        else:
            continue

        year = int(row["TIME_PERIOD"])
        key = (year, field)
        if key in seen:
            raise FetchError(f"duplicate selected observation: {key}")
        seen.add(key)
        value = float(row["OBS_VALUE"])
        if field == "death_rate_per_1000":
            value /= 100.0
        out.setdefault(year, {})[field] = value

    required = {"deaths_all", "death_rate_per_1000",
                "malignant_neoplasms_per_100k", "circulatory_per_100k"}
    years = sorted(y for y, values in out.items() if required <= values.keys())
    if not years or years[0] > 2005 or years[-1] < 2023:
        raise FetchError(f"unexpected complete coverage: {years[:1]}..{years[-1:]}")

    baseline_years = range(2015, 2020)
    try:
        baseline = sum(out[y]["deaths_all"] for y in baseline_years) / 5
    except KeyError as exc:
        raise FetchError(f"missing 2015-2019 baseline observation: {exc}") from exc
    for year, values in out.items():
        if year >= 2015 and "deaths_all" in values:
            values["excess_pct"] = (values["deaths_all"] / baseline - 1) * 100

    for (year, field), expected in SPOT.items():
        got = out.get(year, {}).get(field)
        if got is None or abs(got - expected) > 0.05:
            raise FetchError(
                f"known-value check failed: {year} {field}={got}, expected {expected}"
            )
    return out


def write(rows: dict[int, dict[str, float]]) -> Path:
    DATA.mkdir(parents=True, exist_ok=True)
    path = DATA / "mortality_from_oecd.csv"
    fields = [
        "year", "deaths_all", "death_rate_per_1000", "excess_pct",
        "covid_deaths", "covid_per_100k",
        "malignant_neoplasms_per_100k", "circulatory_per_100k",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for year in sorted(rows):
            values = rows[year]
            writer.writerow({
                "year": year,
                "deaths_all": f"{values['deaths_all']:.0f}",
                "death_rate_per_1000": f"{values['death_rate_per_1000']:.3f}",
                "excess_pct": (
                    f"{values['excess_pct']:.2f}" if "excess_pct" in values else ""
                ),
                "covid_deaths": (
                    f"{values['covid_deaths']:.0f}" if "covid_deaths" in values else ""
                ),
                "covid_per_100k": (
                    f"{values['covid_per_100k']:.1f}"
                    if "covid_per_100k" in values else ""
                ),
                "malignant_neoplasms_per_100k": (
                    f"{values['malignant_neoplasms_per_100k']:.1f}"
                ),
                "circulatory_per_100k": f"{values['circulatory_per_100k']:.1f}",
            })
    return path


def main() -> None:
    path = write(selected(get()))
    print(f"OECD Causes of Mortality -> {path.relative_to(ROOT)}")
    print("  annual all-age/both-sex national vital-registration data, 2005-2023")
    print("  excess baseline: arithmetic mean of 2015-2019 all-cause counts")


if __name__ == "__main__":
    main()
