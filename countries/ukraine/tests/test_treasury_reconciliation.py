"""Treasury vintage audit: annual data agree, December snapshot differs."""
from __future__ import annotations

from decimal import Decimal
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "fetch" / "audit_open_budget.py"
spec = importlib.util.spec_from_file_location("treasury_portal_audit", SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def evidence():
    return audit._read(audit.NBU_CSV), audit._read(audit.OPEN_BUDGET_CSV)


def test_official_dashboard_matches_its_own_functional_total():
    nbu, portal = evidence()
    rows = audit.reconcile(nbu, portal)
    assert len(rows) == 11
    assert {r["year"] for r in rows} == {"2025"}
    assert sum(Decimal(r["open_budget_million_uah"])
               for r in rows if r["classification"] != "gf_budgtef_Total_1") == (
                   Decimal("5999467.11164619"))


def test_NBU_and_earlier_december_edition_are_not_falsely_equated():
    rows = {r["classification"]: r for r in audit.reconcile(*evidence())}
    assert rows["gf_budgtef_0200"]["reconciliation_status"] == "within_nbu_rounding"
    assert rows["gf_budgtef_0400"]["reconciliation_status"] == (
        "earlier_december_edition_differs")
    assert Decimal(rows["gf_budgtef_0400"]["nbu_minus_open_budget_million_uah"]) == (
        Decimal("6892.20539300"))
    assert Decimal(rows["gf_budgtef_Total_1"]["nbu_minus_open_budget_million_uah"]) == (
        Decimal("6920.18835381"))
    different = [r for r in rows.values() if "edition_differs" in r["reconciliation_status"]]
    assert len(different) == 5, "December-to-annual revision baseline changed"


def test_schema_and_source_perimeter_mismatches_fail():
    for field, value, pattern in (
        ("publisher_classification_code", "COFOG_04", "Unknown"),
        ("year", "2024", "period/perimeter"),
        ("perimeter", "SBU", "period/perimeter"),
        ("value_million_uah", "-99", "Negative"),
        ("reference_url", "https://example.com/2025", "attribution"),
    ):
        nbu, portal = evidence()
        portal[0] = {**portal[0], field: value}
        with pytest.raises(ValueError, match=pattern):
            audit.reconcile(nbu, portal)


def test_duplicates_and_missing_functional_groups_fail():
    nbu, portal = evidence()
    with pytest.raises(ValueError, match="duplicate|Duplicate"):
        audit.reconcile(nbu, [*portal[:-1], portal[0]])
    with pytest.raises(ValueError, match="missing"):
        audit.reconcile(nbu, portal[:-1])


def test_independent_portal_accounting_identity_is_strict():
    nbu, portal = evidence()
    portal[0] = {**portal[0], "value_million_uah": "512181.58289890"}
    with pytest.raises(ValueError, match="does not reconcile"):
        audit.reconcile(nbu, portal)


def test_no_live_network_or_curated_csv_write_paths():
    assert audit.REPORT.parent.name == "cache"
    assert audit.REPORT.name.endswith("_check.csv")
    assert audit.NBU_CSV.name == "treasury_functional.csv"
    assert audit.NBU_CSV.parent.name == "fiscal"
    assert audit.OPEN_BUDGET_CSV.parent.name == "fetch"
    assert "general_government" not in audit.csv_text(audit.reconcile(*evidence()))


def test_2025_calendar_mapping_is_nonnegotiable():
    nbu, portal = evidence()
    nbu[-1] = {**nbu[-1], "source_dt": "20250101"}
    with pytest.raises(ValueError, match="year-end mapping"):
        audit.reconcile(nbu, portal)


def test_trilingual_fiscal_disclosure_keeps_existing_imf_plate():
    """Nine published topics survive and the Treasury source has its own notes."""
    import json
    ui = json.loads((ROOT / "ui.json").read_text(encoding="utf-8"))
    for language, term in (
        ("en", "National Treasury cash execution"),
        ("uk", "Касове виконання Казначейства"),
        ("pt", "Execução de caixa do Tesouro"),
    ):
        matches = [x for x in ui[language]["colophon"] if x["term"] == term]
        assert len(matches) == 1, f"{language}: cash-budget source missing"
        claim = matches[0]["detail"]
        assert "2011" in claim and "2025" in claim
        assert "6.92" in claim or "6,92" in claim
        assert ("IMF" in claim or "МВФ" in claim or "FMI" in claim)
        assert not any(x["term"] in ("Public finances", "Державні фінанси",
                                     "Contas públicas")
                       for x in ui[language]["unavailable"])



def test_treasury_dataset_is_not_misrepresented_as_comparable_gg():
    """Official cash data may appear in source table, never as a canonical slot."""
    from core.country import Country
    from core import sitebuild
    country = Country.load("ukraine")
    dataset = [d for d in sitebuild.datasets_for(country)
               if d["file"] == "fiscal/treasury_functional.csv"]
    assert len(dataset) == 1
    assert dataset[0]["official"] is True
    assert dataset[0]["coverage"] == "2011-2025"
    assert "Treasury" in dataset[0]["publisher"]
    import importlib.util
    module_path = country.dir / "plates.py"
    spec = importlib.util.spec_from_file_location("ukraine_fiscal_country_plates", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # The chapter set the edition publishes now. The Treasury dataset is
    # drawn only inside `spending`, always labelled as cash-basis Treasury
    # execution and never as general-government accrual — the check below
    # names the plate that reads it.
    assert {entry["topic"] for entry in module.PLATES} == {
        "economy", "fiscal", "spending", "trade", "markets", "people",
        "world", "demography", "security", "mortality", "migration"
    }
    spending = [e for e in module.PLATES if e["topic"] == "spending"]
    assert len(spending) == 1
    source = module_path.read_text(encoding="utf-8")
    assert "fiscal/treasury_functional.csv" in source
    assert "IMF accrual layer" in source



def test_mof_annual_outturn_reconciles_nbu_at_published_precision():
    nbu, _ = evidence()
    annual = audit._read(audit.MOF_ANNUAL_CSV)
    rows = audit.reconcile_annual(nbu, annual)
    assert len(rows) == 11
    assert {r["reconciliation_status"] for r in rows} == {
        "independent_annual_confirmation"}
    by_code = {r["classification"]: r for r in rows}
    assert Decimal(by_code["gf_budgtef_Total_1"]["mof_annual_million_uah"]) == (
        Decimal("6006387.27484437"))
    assert Decimal(by_code["gf_budgtef_0400"]["mof_annual_million_uah"]) == (
        Decimal("264998.32655720"))
    assert Decimal(by_code["gf_budgtef_0200"]["mof_annual_million_uah"]) == (
        Decimal("3069857.41825598"))
    assert all(abs(Decimal(r["nbu_minus_mof_annual_million_uah"]))
               <= audit.HALF_ROUND_UNIT for r in rows)


def test_mof_annual_version_change_or_schema_break_fails():
    nbu, _ = evidence()
    valid = audit._read(audit.MOF_ANNUAL_CSV)
    for key, value, pattern in [
        ("source_edition", "December edition", "identity"),
        ("workbook_sheet", "грудень", "identity"),
        ("year", "2024", "period/perimeter"),
        ("perimeter", "SBU", "period/perimeter"),
        ("value_million_uah", "-1", "Negative"),
    ]:
        altered = [dict(r) for r in valid]
        altered[0][key] = value
        with pytest.raises(ValueError, match=pattern):
            audit.reconcile_annual(nbu, altered)
    with pytest.raises(ValueError, match="incomplete"):
        audit.reconcile_annual(nbu, valid[:-1])
    altered = [dict(r) for r in valid]
    altered[0]["value_million_uah"] = "600000.00"
    with pytest.raises(ValueError, match="does not reconcile"):
        audit.reconcile_annual(nbu, altered)
    altered = [dict(r) for r in valid]
    altered[0]["value_million_uah"] = str(
        Decimal(altered[0]["value_million_uah"]) + Decimal("0.10"))
    altered[-1]["value_million_uah"] = str(
        Decimal(altered[-1]["value_million_uah"]) + Decimal("0.10"))
    with pytest.raises(ValueError, match="source-vintage mismatch"):
        audit.reconcile_annual(nbu, altered)
