"""Offline regression contracts for Ukraine Treasury cash functional expenditure.

Synthetic fixture rows exercise parser safeguards; only the 2023–2025
Ministry of Finance anchors represent actual independently published values.
"""
from __future__ import annotations

import csv
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import unittest

BASE = Path(__file__).resolve().parents[1]
PARSER = BASE / "fetch" / "fetch_treasury.py"
spec = importlib.util.spec_from_file_location("ukraine_treasury", PARSER)
treasury = importlib.util.module_from_spec(spec)
spec.loader.exec_module(treasury)


def sample(change=None, omit=None, duplicate=None):
    data = []
    anchors = treasury.ANCHORS
    for year in range(treasury.START, treasury.END + 1):
        for code, _ in (*treasury.CATEGORIES, (treasury.TOTAL, "total_million_uah")):
            key = (year, code)
            if key == omit:
                continue
            amount = anchors.get(key, Decimal("1000") if code == treasury.TOTAL
                                 else Decimal("100"))
            # Fill all OTHER synthetic categories so the independent
            # publisher anchors reconcile without fabricating observations.
            if year in (2023, 2024, 2025) and key not in anchors:
                anchored_categories = [(year, c) for c, _ in treasury.CATEGORIES
                                       if (year, c) in anchors]
                remainder_count = len(treasury.CATEGORIES) - len(anchored_categories)
                amount = ((anchors[(year, treasury.TOTAL)] -
                           sum((anchors[k] for k in anchored_categories), Decimal(0)))
                          / Decimal(remainder_count))
            row = {"dt": f"{year + 1}0101", "txt": "Функція",
                   "txten": "Treasury expenditure",
                   "id_api": code, "leveli": 1 if code == treasury.TOTAL else 2,
                   "parent": "budgtef_Total_2" if code == treasury.TOTAL
                   else "budgtef_Total_1", "freq": "Y", "mcr200p": "CBU",
                   "tzep": "F_M_VC", "value": str(amount)}
            if change and key == change[0]:
                row.update(change[1])
            data.append(row)
            if duplicate == key:
                data.append(dict(row))
        data.append({"dt": f"{year + 1}0101", "id_api": "gf_budgtef_0200",
                     "freq": "Y", "mcr200p": "SBU", "value": "99999999"})
    return json.dumps(data).encode()


class TreasuryTests(unittest.TestCase):
    def test_calendar_year_is_previous_year_and_state_rows_ignored(self):
        rows = treasury.parse(sample())
        self.assertEqual(len(rows), 15)
        self.assertEqual([int(x["year"]) for x in rows], list(range(2011, 2026)))
        self.assertEqual(rows[-3]["source_dt"], "20240101")
        self.assertEqual(rows[-3]["year"], "2023")
        self.assertEqual(rows[-2]["source_dt"], "20250101")
        self.assertEqual(rows[-2]["defence_million_uah"], "2305242.7")

    def test_schema_duplicates_gaps_and_unit_fail_closed(self):
        key = (2020, "gf_budgtef_0200")
        for mutation, expected in [
            ({"tzep": "F_Y_V"}, "unit"),
            ({"leveli": 3}, "hierarchy"),
            ({"parent": "budgtef_Total_2"}, "hierarchy"),
            ({"dt": "20200101"}, "Duplicate|Incomplete"),
            ({"dt": "20210202"}, "date"),
            ({"txten": ""}, "label"),
            ({"value": "-3"}, "Implausible"),
            ({"value": "NaN"}, "Implausible"),
        ]:
            with self.subTest(mutation=mutation), self.assertRaisesRegex(
                ValueError, expected
            ):
                treasury.parse(sample(change=(key, mutation)))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            treasury.parse(sample(duplicate=key))
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            treasury.parse(sample(omit=key))

    def test_independent_official_anchors_must_match_all_years(self):
        for year in (2023, 2024, 2025):
            key = (year, "gf_budgtef_0200")
            with self.assertRaisesRegex(ValueError, "Ministry of Finance anchor"):
                treasury.parse(sample(change=(key, {"value": "1"})))

    def test_2025_annual_economic_affairs_anchor(self):
        key = (2025, "gf_budgtef_0400")
        with self.assertRaisesRegex(ValueError, "Ministry of Finance anchor"):
            treasury.parse(sample(change=(key, {"value": "258106.1"})))

    def test_totals_do_not_permit_accounting_scope_substitution(self):
        key = (2019, "gf_budgtef_0200")
        with self.assertRaisesRegex(ValueError, "accounting mismatch"):
            treasury.parse(sample(change=(key, {"value": "600"})))
        with self.assertRaises(ValueError):
            treasury.parse(b"<html>Access Denied</html>")
        with self.assertRaises(ValueError):
            treasury.parse(b"[]")

    def test_no_curated_overwrite_and_source_identity(self):
        self.assertEqual(treasury.SIDECAR.name, "treasury_functional_from_nbu.csv")
        # Relative to the country directory, so a checkout under a path that
        # itself contains "/data/" (as this machine's does) is not a failure.
        rel = treasury.SIDECAR.relative_to(treasury.HERE.parent.parent).as_posix()
        self.assertNotIn("/data/", rel)
        self.assertEqual(treasury.PERIMETER, "CBU")
        self.assertEqual(treasury.UNIT, "F_M_VC")
        self.assertEqual(treasury.FREQ, "Y")
        csv_text = treasury.as_csv(treasury.parse(sample()))
        self.assertTrue(csv_text.startswith("year,source_dt,"))
        self.assertNotIn("general_government", csv_text)

    def test_curated_history_complete_accounted_and_year_aligned(self):
        path = BASE / "data" / "fiscal" / "treasury_functional.csv"
        with path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 15)
        self.assertEqual(set(rows[0]), set(treasury.FIELDS))
        for expected_year, row in enumerate(rows, 2011):
            year = int(row["year"])
            self.assertEqual(year, expected_year)
            self.assertEqual(row["source_dt"], f"{year + 1}0101")
            parts = sum((Decimal(row[field]) for _, field in treasury.CATEGORIES),
                        Decimal("0"))
            total = Decimal(row["total_million_uah"])
            self.assertLessEqual(abs(parts - total), Decimal("0.5"))
            self.assertGreater(total, 0)
        index = {int(r["year"]): r for r in rows}
        for (year, code), value in treasury.ANCHORS.items():
            field = dict(treasury.CATEGORIES).get(code, "total_million_uah")
            self.assertEqual(Decimal(index[year][field]), value)


if __name__ == "__main__":
    unittest.main()
