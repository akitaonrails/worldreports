#!/usr/bin/env python3
"""Refresh Russia's FEDERAL budget from the Ministry of Finance's workbook.

Usage:  make C=russia fetch   (or: python3 -I fetch/fetch_minfin.py)

The Ministry of Finance publishes federal budget execution — cash, one
level of government — as a single annual workbook. It answered 200 on
2026-10-25 while the customs service and data.gov.ru did not connect.

  Приложение 3.1  "Краткая информация об исполнении федерального
  бюджета", sheet «год»: revenue (total, oil and gas, non-oil and gas),
  expenditure by the national functional classification (14 sections),
  the deficit or surplus, and the non-oil-and-gas deficit. Billion
  roubles, 2006-2025, one column per year.

THIS IS NOT THE GENERAL GOVERNMENT
----------------------------------
The spine's fiscal slots are general government, and those come from the
IMF WEO (fiscal/fiscal_from_imf.csv). The federal budget is a different
perimeter — one level of government, cash execution, no regional or
social-fund budgets — and it is the series Russian fiscal argument is
actually about: the oil-and-gas share of revenue and the non-oil-and-gas
deficit are the two numbers the Ministry itself leads with. The two are
staged as two files and drawn as two labelled lines, never spliced.

THE FUNCTIONAL CLASSIFICATION IS NOT COFOG
------------------------------------------
The 14 sections are the Russian budget classification, in force since
2005 (the workbook's own footnote says the classification applied in the
corresponding year). They map onto the spine's seven spending groups where
the mapping is clean and the note says where it is not; the mapping lives
in DATA_NOTES.md and in the curated data/spending file, not in this
fetcher, which writes the publisher's own sections unmodified.
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"

# The annual edition. The quarterly and monthly editions sit beside it at
# .../Prilozhenie_3_dannye_109-111_—_kvartal.xlsx and _mes.xlsx.
URL = ("https://minfin.gov.ru/common/upload/library/2026/05/main/"
       "Prilozhenie_3_dannye_109-111_%E2%80%94_god.xlsx")
NAME = "minfin_fedbudget_god.xlsx"

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/126.0"}
YEAR_FROM, YEAR_TO = 2006, 2026

# Row labels in the publisher's sheet, matched on a prefix of column B so
# that the numbering ('2.2.') and the wording both have to agree.
ROWS = {
    "revenue": "Доходы, всего",
    "oil_gas_revenue": "Нефтегазовые доходы",
    "non_oil_gas_revenue": "Ненефтегазовые доходы",
    "expenditure": "Расходы, всего",
    "balance": "Дефицит (-)/Профицит (+)",
    "non_oil_gas_balance": "Ненефтегазовый дефицит",
}

# The functional sections, in the publisher's order. Keyed by the label
# that follows the section number in column B.
SECTIONS = [
    ("general_government", "Общегосударственные вопросы"),
    ("national_defence", "Национальная оборона"),
    ("security_law_order", "Национальная безопасность и правоохранительная"),
    ("national_economy", "Национальная экономика"),
    ("housing_utilities", "Жилищно-коммунальное хозяйство"),
    ("environment", "Охрана окружающей среды"),
    ("education", "Образование"),
    ("culture_media", "Культура, кинематография и средства массовой"),
    ("health", "Здравоохранение и спорт"),
    ("social_policy", "Социальная политика"),
    ("physical_culture", "Физическая культура и спорт"),
    ("media", "Средства массовой информации"),
    ("debt_service", "Обслуживание государственного и муниципального долга"),
    ("interbudgetary", "Межбюджетные трансферты"),
]


def download() -> Path:
    CACHE.mkdir(exist_ok=True)
    path = CACHE / NAME
    if path.exists() and path.read_bytes()[:2] == b"PK":
        return path
    req = urllib.request.Request(URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=180) as r:
        raw = r.read()
    if raw[:2] != b"PK" or len(raw) < 4000:
        sys.exit(f"{NAME}: not an xlsx ({len(raw)} bytes) — an HTML error "
                 "page under HTTP 200 is not data")
    path.write_bytes(raw)
    return path


def parse(path: Path) -> tuple[dict[int, dict[str, float]], list[int]]:
    """{(row key, year): billion roubles} plus the year columns."""
    import warnings

    import openpyxl

    warnings.filterwarnings("ignore", module="openpyxl")
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    head = None
    for row in rows[:6]:
        years = [c for c in row[2:] if isinstance(c, int) and 1990 < c < 2200]
        if len(years) >= 10:
            head = row
            break
    if head is None:
        sys.exit("minfin: no year header row")
    year_cols = [(i, int(c)) for i, c in enumerate(head)
                 if isinstance(c, int) and 1990 < c < 2200]

    wanted = dict(ROWS)
    for key, label in SECTIONS:
        wanted[key] = label

    out: dict[int, dict[str, float]] = {}
    for row in rows:
        label = str(row[1] or "").strip() if len(row) > 1 else ""
        if not label:
            continue
        for key, prefix in wanted.items():
            if not label.startswith(prefix):
                continue
            for i, year in year_cols:
                if i >= len(row):
                    continue
                value = row[i]
                if isinstance(value, (int, float)):
                    out.setdefault(year, {})[key] = float(value)
    return out, [y for _, y in year_cols]


def write(rel: str, header: list[str], rows: list[list[str]],
          comments: list[str]) -> None:
    path = ROOT / "data" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {c}" for c in comments]
    lines.append(",".join(header))
    lines += [",".join(r) for r in rows]
    path.write_text("\n".join(lines) + "\n")
    print(f"  data/{rel}  {len(rows)} rows")


def main() -> None:
    print("Ministry of Finance: federal budget execution")
    data, years = parse(download())

    # ---- known observations ---------------------------------------------
    # Federal revenue 2006 = 6,278.9 bn roubles and expenditure =
    # 5,983.1 bn, a surplus of +1,995.0 bn in 2007 — the oil boom. 2023
    # revenue 29,124 bn, expenditure 32,364 bn, deficit -3,240 bn, which
    # the Ministry's own annual release states.
    assert abs(data[2006]["revenue"] - 6278.9) < 1.0, data[2006]["revenue"]
    assert abs(data[2007]["balance"] - 1794.6) < 5.0, data[2007]["balance"]
    assert abs(data[2023]["revenue"] - 29124.0) < 60.0, data[2023]["revenue"]
    assert abs(data[2023]["expenditure"] - 32364.0) < 60.0, data[2023]["expenditure"]
    assert abs(data[2023]["balance"] + 3240.0) < 60.0, data[2023]["balance"]

    # 'debt_service' is the same row the publisher numbers 2.13; it is
    # carried once, here as interest paid, and once in the functional file
    # because the functional classification includes it as a section.
    main_cols = ["revenue", "oil_gas_revenue", "non_oil_gas_revenue",
                 "expenditure", "balance", "non_oil_gas_balance",
                 "debt_service"]
    write("fiscal/federal_budget_from_minfin.csv",
          ["year"] + [f"{c}_bn_rub" for c in main_cols],
          [[str(y)] + [f"{data[y][c]:.1f}" if c in data.get(y, {}) else ""
                       for c in main_cols]
           for y in sorted(data) if YEAR_FROM <= y <= YEAR_TO],
          ["Ministry of Finance of the Russian Federation, Приложение 3.1",
           "'Краткая информация об исполнении федерального бюджета', sheet",
           "'год': federal budget execution, BILLION ROUBLES, cash basis,",
           "FEDERAL level only.",
           "NOT general government: no regional budgets, no state social",
           "funds, no accrual. The spine's fiscal slots use the IMF WEO",
           "general-government series; this is the national line beside it.",
           "balance is the publisher's 'Дефицит (-)/Профицит (+)';",
           "non_oil_gas_balance is the non-oil-and-gas deficit the Ministry",
           "leads with. interest is section 2.13, debt service.",
           "Fetched 2026-10-25."])

    write("spending/federal_function_from_minfin.csv",
          ["year"] + [k for k, _ in SECTIONS],
          [[str(y)] + [f"{data[y][k]:.1f}" if k in data.get(y, {}) else ""
                       for k, _ in SECTIONS]
           for y in sorted(data) if YEAR_FROM <= y <= YEAR_TO],
          ["Ministry of Finance, Приложение 3.1, sheet 'год': federal budget",
           "EXPENDITURE by the national functional classification, BILLION",
           "ROUBLES, cash basis, federal level only.",
           "This is the Russian budget classification, NOT COFOG. The",
           "workbook's own footnote states the classification applied in the",
           "corresponding year; the sections changed in 2005 and again with",
           "the 2013 programme-based reform, so a section's level is not",
           "strictly comparable across the whole window.",
           "health is section 2.9 'Здравоохранение и спорт', which bundles",
           "sport until 2011 when sport became its own section 2.11;",
           "physical_culture and media are separate sections from then on.",
           "THE FUNCTIONAL BREAKDOWN STOPS IN 2021. Columns 2022-2025 are",
           "empty in the publisher's annual workbook while the totals in",
           "fiscal/federal_budget_from_minfin.csv continue to 2025: federal",
           "budget spending by section has not been published since the",
           "2022 classification of budget data. The hole is the finding and",
           "is not filled from any other source.",
           "Fetched 2026-10-25."])


if __name__ == "__main__":
    main()
