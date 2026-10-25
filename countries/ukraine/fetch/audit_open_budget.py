#!/usr/bin/env python3
"""Read-only audit of 2025 Treasury fiscal publication vintages.

The NBU aligns with the Ministry of Finance ANNUAL 2025 outturn, while
its earlier DECEMBER 2025 edition differs. Both editions remain traceable;
this audit never overwrites committed curated data.
"""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
from io import StringIO
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
NBU_CSV = BASE / "data" / "fiscal" / "treasury_functional.csv"
OPEN_BUDGET_CSV = Path(__file__).resolve().parent / "reference_openbudget_2025.csv"
MOF_ANNUAL_CSV = Path(__file__).resolve().parent / "reference_mof_2025_annual.csv"
ANNUAL_REPORT = Path(__file__).resolve().parent / "cache" / "treasury_annual_confirmation_check.csv"
REPORT = Path(__file__).resolve().parent / "cache" / "treasury_reconciliation_check.csv"
CODES = {
    "gf_budgtef_0100": "general_public_services_million_uah",
    "gf_budgtef_0200": "defence_million_uah",
    "gf_budgtef_0300": "public_order_safety_judiciary_million_uah",
    "gf_budgtef_0400": "economic_affairs_million_uah",
    "gf_budgtef_0500": "environment_million_uah",
    "gf_budgtef_0600": "housing_community_million_uah",
    "gf_budgtef_0700": "health_million_uah",
    "gf_budgtef_0800": "culture_recreation_religion_million_uah",
    "gf_budgtef_0900": "education_million_uah",
    "gf_budgtef_1000": "social_protection_million_uah",
    "gf_budgtef_Total_1": "total_million_uah",
}
ANNUAL_HEADERS = ("year", "classification", "nbu_million_uah",
                  "mof_annual_million_uah", "nbu_minus_mof_annual_million_uah",
                  "reconciliation_status")
HEADERS = ("year", "classification", "nbu_million_uah",
           "open_budget_million_uah", "nbu_minus_open_budget_million_uah",
           "reconciliation_status")
HALF_ROUND_UNIT = Decimal("0.05")  # NBU rounds nominal million UAH to 0.1


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise ValueError(f"Empty fiscal evidence: {path.name}")
    return rows


def _number(value: str) -> Decimal:
    try:
        d = Decimal(value)
    except (TypeError, ValueError, InvalidOperation) as exc:
        raise ValueError("Non-numeric official fiscal observation") from exc
    if not d.is_finite() or d < 0:
        raise ValueError("Negative or nonfinite fiscal expenditure")
    return d


def reconcile(nbu: list[dict[str, str]],
              open_budget: list[dict[str, str]]) -> list[dict[str, str]]:
    # This is a same-year classification cross-check, NOT a comparable-GG
    # account and NOT a license to overwrite the NBU source of truth.
    year_nbu = [r for r in nbu if r.get("year") == "2025"]
    if len(year_nbu) != 1 or year_nbu[0].get("source_dt") != "20260101":
        raise ValueError("NBU 2025 year-end mapping changed")
    row = year_nbu[0]
    if len(open_budget) != len(CODES):
        raise ValueError("Open Budget reference missing or unexpected classifications")
    reference: dict[str, Decimal] = {}
    for item in open_budget:
        code = item.get("publisher_classification_code")
        if code not in CODES:
            raise ValueError(f"Unknown Open Budget functional category: {code}")
        if code in reference:
            raise ValueError(f"Duplicate Open Budget category: {code}")
        if item.get("year") != "2025" or item.get("perimeter") != "CBU":
            raise ValueError("Reference period/perimeter mismatch")
        if item.get("publisher") != "Open Budget (State portal)" or (
            "budgetType=CONSOLIDATED" not in item.get("reference_url", "")
            or "year=2025" not in item.get("reference_url", "")
        ):
            raise ValueError("Official source attribution or query changed")
        reference[code] = _number(item.get("value_million_uah", ""))
    if set(reference) != set(CODES):
        raise ValueError("Incomplete Open Budget functional categories")
    # The independent dashboard's categories must account for its own total
    # to 0.01 UAH (0.00000001 million), not just NBU's rounded precision.
    parts = sum((v for c, v in reference.items()
                 if c != "gf_budgtef_Total_1"), Decimal(0))
    if abs(parts - reference["gf_budgtef_Total_1"]) > Decimal("0.00000001"):
        raise ValueError("Open Budget hierarchy does not reconcile internally")
    result = []
    for code, col in CODES.items():
        current = _number(row.get(col, ""))
        other = reference[code]
        diff = current - other
        result.append({
            "year": "2025", "classification": code,
            "nbu_million_uah": str(current),
            "open_budget_million_uah": str(other),
            "nbu_minus_open_budget_million_uah": str(diff),
            "reconciliation_status": ("within_nbu_rounding"
                                      if abs(diff) <= HALF_ROUND_UNIT
                                      else "earlier_december_edition_differs"),
        })
    return result


def reconcile_annual(nbu: list[dict[str, str]],
                     mof_annual: list[dict[str, str]]) -> list[dict[str, str]]:
    """Compare official MoF annual outturn with the identically dated NBU.

    The Ministry annual workbook splits national code 0100 into two lines,
    public services excluding debt-service and debt-service. The reference
    CSV adds only these two subcomponents to form code 0100.
    """
    current = [r for r in nbu if r.get("year") == "2025"]
    if len(current) != 1 or current[0].get("source_dt") != "20260101":
        raise ValueError("NBU 2025 year-end mapping changed")
    if len(mof_annual) != len(CODES):
        raise ValueError("MoF annual reference incomplete")
    values = {}
    for row in mof_annual:
        code = row.get("publisher_classification_code")
        if code not in CODES or code in values:
            raise ValueError(f"Unexpected or duplicated annual category: {code}")
        if row.get("year") != "2025" or row.get("perimeter") != "CBU":
            raise ValueError("MoF annual period/perimeter mismatch")
        if (row.get("publisher") != "Ministry of Finance of Ukraine"
            or row.get("source_edition") != "Annual outturn 2025"
            or "mof.gov.ua/storage/files/" not in row.get("reference_url", "")
            or row.get("workbook_sheet") != "2025 рік"):
            raise ValueError("MoF annual publication identity changed")
        values[code] = _number(row.get("value_million_uah", ""))
    if set(values) != set(CODES):
        raise ValueError("MoF annual functional categories incomplete")
    parts = sum((v for k, v in values.items() if k != "gf_budgtef_Total_1"),
                Decimal(0))
    if abs(parts - values["gf_budgtef_Total_1"]) > Decimal("0.00000001"):
        raise ValueError("MoF annual functional total does not reconcile")
    result = []
    for code, col in CODES.items():
        n = _number(current[0].get(col, ""))
        mof = values[code]
        diff = n - mof
        if abs(diff) > HALF_ROUND_UNIT:
            raise ValueError(f"MoF annual/NBU source-vintage mismatch at {code}: {diff}")
        result.append({
            "year": "2025", "classification": code, "nbu_million_uah": str(n),
            "mof_annual_million_uah": str(mof),
            "nbu_minus_mof_annual_million_uah": str(diff),
            "reconciliation_status": "independent_annual_confirmation",
        })
    return result


def csv_text(rows: list[dict[str, str]], fields=HEADERS) -> str:
    out = StringIO()
    writer = csv.DictWriter(out, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def main() -> None:
    nbu = _read(NBU_CSV)
    december = reconcile(nbu, _read(OPEN_BUDGET_CSV))
    annual = reconcile_annual(nbu, _read(MOF_ANNUAL_CSV))
    reports = [(REPORT, csv_text(december)),
               (ANNUAL_REPORT, csv_text(annual, ANNUAL_HEADERS))]
    for path, content in reports:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(path)
    differences = [r for r in december
                   if r["reconciliation_status"] == "earlier_december_edition_differs"]
    print(f"Fiscal audit: {len(annual)} MoF annual/NBU observations agree; "
          f"{len(differences)} December-edition differences.")
    print("Annual source matches NBU to published precision. The specific "
          "administrative reasons for December-to-annual revisions are unverified.")
    print(f"Review-only reports: {REPORT}; {ANNUAL_REPORT}")

if __name__ == "__main__":
    main()
