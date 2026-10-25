#!/usr/bin/env python3
"""Stage the NBU-republished Treasury functional expenditure as a review sidecar.

This source measures *consolidated budget CASH execution*, not harmonised
general-government accrual expenditure or COFOG. The NBU's January-1 stamp
labels the END of the preceding calendar year's expenditure: 20240101 is 2023.
Never use this as a canonical fiscal.%GDP or spending.%GDP spine series.
"""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
from io import StringIO
import json
from pathlib import Path
from urllib.request import Request, urlopen

URL = "https://bank.gov.ua/NBUStatService/v1/statdirectory/budget?json"
HERE = Path(__file__).resolve().parent
SIDECAR = HERE / "cache" / "treasury_functional_from_nbu.csv"
START, END = 2011, 2025
PERIMETER, UNIT, FREQ = "CBU", "F_M_VC", "Y"
CATEGORIES = (
    ("gf_budgtef_0100", "general_public_services_million_uah"),
    ("gf_budgtef_0200", "defence_million_uah"),
    ("gf_budgtef_0300", "public_order_safety_judiciary_million_uah"),
    ("gf_budgtef_0400", "economic_affairs_million_uah"),
    ("gf_budgtef_0500", "environment_million_uah"),
    ("gf_budgtef_0600", "housing_community_million_uah"),
    ("gf_budgtef_0700", "health_million_uah"),
    ("gf_budgtef_0800", "culture_recreation_religion_million_uah"),
    ("gf_budgtef_0900", "education_million_uah"),
    ("gf_budgtef_1000", "social_protection_million_uah"),
)
TOTAL = "gf_budgtef_Total_1"
# Maintainer extension: capital expenditure is an economic, not a
# functional, line, so it is carried in its own column and kept out
# of the functional total (the identity below would otherwise break).
CAPITAL = "gf_budgtee_3000"
FIELDS = ("year", "source_dt", *(field for _, field in CATEGORIES),
          "capital_million_uah", "total_million_uah")
REQUIRED = frozenset(("dt", "txt", "txten", "id_api", "leveli",
                      "parent", "freq", "mcr200p", "tzep", "value"))
# Ministry of Finance, Budget of Ukraine 2024, §2.3 pp. 34–37:
# https://mof.gov.ua/storage/files/Badgef%20of%20Ukraine2024.pdf
# The 2025 annual published edition independently checks the NBU vintage:
# https://www.mof.gov.ua/storage/files/4_%D0%97%D0%91_%D1%80%D1%96%D0%BA_%D1%81%D0%B0%D0%B9%D1%82_25.xlsx
# Independent anchors also prove the NBU's year-end timestamp convention.
ANCHORS = {
    (2023, "gf_budgtef_0200"): Decimal("2097621.9"),
    (2023, TOTAL): Decimal("4441364.6"),
    (2024, "gf_budgtef_0200"): Decimal("2305242.7"),
    (2024, TOTAL): Decimal("4945680.7"),
    # MoF annual consolidated outturn workbook for 2025, sheet "2025 рік".
    # This is the REVISED ANNUAL edition, not its earlier December release.
    (2025, "gf_budgtef_0200"): Decimal("3069857.4"),
    (2025, "gf_budgtef_0400"): Decimal("264998.3"),
    (2025, TOTAL): Decimal("6006387.3"),
}


def fetch() -> bytes:
    request = Request(URL, headers={"Accept": "application/json",
                                   "User-Agent": "WorldReports-country-sourcing/1.0"})
    with urlopen(request, timeout=90) as response:
        mime = response.headers.get("Content-Type", "").lower()
        body = response.read(25_000_001)
        if response.status != 200 or "json" not in mime:
            raise ValueError("NBU did not return an HTTP 200 JSON document")
    if not body or len(body) > 25_000_000:
        raise ValueError("NBU response empty or oversized")
    return body


def parse(raw: bytes) -> list[dict[str, str]]:
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("NBU response is not valid UTF-8 JSON") from exc
    if not isinstance(payload, list) or len(payload) < 100:
        raise ValueError("NBU budget cube missing or incomplete")

    codes = dict(CATEGORIES)
    wanted = set(codes) | {TOTAL, CAPITAL}
    by_key: dict[tuple[int, str], Decimal] = {}
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("Unexpected NBU row type")
        code = item.get("id_api")
        if code not in wanted or item.get("freq") != FREQ or item.get("mcr200p") != PERIMETER:
            continue
        if not REQUIRED <= item.keys():
            raise ValueError(f"NBU annual functional schema changed for {code}")
        dt = item["dt"]
        if not isinstance(dt, str) or len(dt) != 8 or not dt.isdigit():
            raise ValueError(f"Invalid annual reference date: {dt!r}")
        # A reference date of January 1 points to the preceding year's outturn.
        year = int(dt[:4]) - 1
        if not START <= year <= END:
            continue
        if dt != f"{year + 1}0101":
            raise ValueError(f"Unexpected Treasury annual date convention: {dt}")
        # Functional annual rows carry F_M_VC. The annual capital line
        # carries F_Y_V up to 2016 and F_M_VC from 2017; the monthly twin
        # is filtered out by FREQ above, so one row per year remains.
        allowed = {"F_Y_V", "F_M_VC"} if code == CAPITAL else {UNIT}
        if item["tzep"] not in allowed:
            raise ValueError(f"Wrong NBU fiscal unit: {year}, {code}")
        if code == CAPITAL:
            # An economic line: no functional parent, so only its own
            # level and the cube's unit are checked.
            if item["leveli"] not in (1, 2, "1", "2"):
                raise ValueError(f"Changed capital hierarchy: {year}")
        else:
            level, parent = ((1, "budgtef_Total_2") if code == TOTAL
                             else (2, "budgtef_Total_1"))
            if item["leveli"] != level or item["parent"] != parent:
                raise ValueError(f"Changed functional hierarchy: {year}, {code}")
        if not isinstance(item["txten"], str) or not item["txten"].strip():
            raise ValueError(f"Missing functional classification label: {year}, {code}")
        key = (year, code)
        if key in by_key:
            raise ValueError(f"Duplicate NBU annual functional record: {key}")
        try:
            amount = Decimal(str(item["value"]))
        except (ValueError, TypeError, InvalidOperation, KeyError) as exc:
            raise ValueError(f"Invalid amount for {key}") from exc
        if not amount.is_finite() or amount < 0 or amount > 50_000_000:
            raise ValueError(f"Implausible nominal expenditure for {key}")
        if key in ANCHORS and amount != ANCHORS[key]:
            raise ValueError(f"Independent Ministry of Finance anchor differs: {key}")
        by_key[key] = amount

    rows = []
    for year in range(START, END + 1):
        missing = (wanted - {CAPITAL}) - {code for (y, code) in by_key if y == year}
        if missing:
            raise ValueError(f"Incomplete functional year {year}: {sorted(missing)}")
        total = by_key[(year, TOTAL)]
        parts = sum((by_key[(year, code)] for code, _ in CATEGORIES), Decimal("0"))
        if abs(parts - total) > Decimal("0.5"):
            raise ValueError(f"Functional category/total accounting mismatch in {year}")
        row = {"year": str(year), "source_dt": f"{year + 1}0101"}
        row.update({field: format(by_key[(year, code)], ".1f")
                    for code, field in CATEGORIES})
        row["capital_million_uah"] = format(by_key.get((year, CAPITAL),
                                                      Decimal("0")), ".1f")
        row["total_million_uah"] = format(total, ".1f")
        rows.append(row)
    return rows


def as_csv(rows: list[dict[str, str]]) -> str:
    f = StringIO()
    writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return f.getvalue()


def main() -> None:
    data = as_csv(parse(fetch()))  # Fail before writing ANYTHING.
    SIDECAR.parent.mkdir(parents=True, exist_ok=True)
    tmp = SIDECAR.with_suffix(".tmp")
    tmp.write_text(data, encoding="utf-8")
    tmp.replace(SIDECAR)
    print(f"Review ONLY: {SIDECAR} (2011–2025, Treasury CBU cash, million UAH)")


if __name__ == "__main__":
    main()
