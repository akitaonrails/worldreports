#!/usr/bin/env python3
"""Fetch the federal budget and the debt from Treasury's Fiscal Data API.

Both series are published by the Treasury itself, with no key:
  mts_table_1    Monthly Treasury Statement — receipts, outlays and the
                 deficit. The September record carries a "Year-to-Date" row,
                 which is the completed fiscal year.
  debt_to_penny  total public debt outstanding, split into debt held by the
                 public and intragovernmental holdings, daily.

Everything here is on a FISCAL year, which for the United States runs from
1 October to 30 September — FY2025 ended 30 September 2025. Ratios to GDP
therefore use a fiscal-year GDP, averaged from BEA's quarterly national
accounts over the same twelve months (Q4 of the previous calendar year
through Q3 of this one), which is how OMB and CBO compute their own. Dividing
a fiscal-year flow by a calendar-year GDP would be a quarter out of step.

Outputs:
  data/fiscal/budget_from_api.csv  fiscal_year,receipts,outlays,deficit,
                                   receipts_pct_gdp,outlays_pct_gdp,
                                   deficit_pct_gdp,fy_gdp,months
  data/fiscal/debt_from_api.csv    fiscal_year,gross,held_by_public,
                                   gross_pct_gdp,public_pct_gdp,asof
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_bea  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "treasury"
DATA = ROOT / "data"
CACHE.mkdir(parents=True, exist_ok=True)

BASE = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"
FY_FROM, FY_TO = 2006, 2026


def get(path: str, params: dict, tag: str) -> list[dict]:
    """One Fiscal Data query, cached. A failure returns nothing rather than
    raising: the committed CSVs do not depend on this running.

    Never narrows the response with `fields`. Asking Fiscal Data for a subset
    of columns makes it GROUP BY what is left and sum the rest, so two rows
    that differ only in a dropped column come back as one row holding their
    total. The Monthly Treasury Statement carries a Year-to-Date row for the
    current fiscal year and another for the prior one, which under a narrowed
    request silently added up to a receipts figure almost twice the real one.
    """
    cache = CACHE / f"{tag}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    try:
        r = requests.get(f"{BASE}{path}", params=params, timeout=120)
        r.raise_for_status()
        rows = r.json().get("data", [])
    except Exception as e:  # noqa: BLE001
        print(f"  !! {tag} failed: {type(e).__name__}: {e}")
        return []
    cache.write_text(json.dumps(rows))
    return rows


def num(v) -> float | None:
    """Fiscal Data writes an absent value as the string 'null'."""
    if v is None or v == "null" or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ------------------------------------------------------------- fiscal-year GDP
def fiscal_year_gdp() -> dict[int, tuple[float, int]]:
    """{fiscal year: (GDP in US$ millions, quarters available)}.

    Current-dollar quarterly GDP is a seasonally adjusted annual rate, so a
    fiscal year is the MEAN of its four quarters, not their sum.
    """
    wb = fetch_bea.workbook(1)
    series, _ = fetch_bea.sheet_series(wb, "T10105-Q")
    quarters = series.get("A191RC", {})
    out: dict[int, tuple[float, int]] = {}
    for fy in range(FY_FROM, FY_TO + 1):
        want = [f"{fy - 1}Q4", f"{fy}Q1", f"{fy}Q2", f"{fy}Q3"]
        got = [quarters[q] for q in want if q in quarters]
        if got:
            out[fy] = (sum(got) / len(got), len(got))
    return out


# ---------------------------------------------------------------------- budget
def budget_rows() -> dict[int, dict]:
    """{fiscal year: its Year-to-Date row} from the September statements.

    A September statement holds two blocks, this fiscal year and the previous
    one, each with its own "Year-to-Date" row. They are told apart by parent:
    the block header is the row labelled "FY 2025", and the Year-to-Date row
    belonging to it names that row as its parent. Matching on the record's
    own `record_fiscal_year` cannot distinguish them — both rows carry it.
    """
    rows = get("/v1/accounting/mts/mts_table_1",
               {"filter": "record_calendar_month:eq:09",
                "page[size]": 10000}, "mts_table_1_sep")
    out: dict[int, dict] = {}
    for fy in range(FY_FROM, FY_TO + 1):
        header = next((r for r in rows
                       if r["classification_desc"] == f"FY {fy}"), None)
        if header is None:
            continue
        ytd = next((r for r in rows
                    if r["classification_desc"] == "Year-to-Date"
                    and r["parent_id"] == header["classification_id"]), None)
        if ytd is not None:
            out[fy] = ytd
    return out


def main() -> None:
    print("Fetching Treasury Fiscal Data...")
    gdp = fiscal_year_gdp()

    # ---- receipts, outlays, deficit -------------------------------------
    # The MTS writes a deficit as a POSITIVE number ("Surplus (+) or Deficit
    # (-)" is the column's own sign convention, and it reports the deficit
    # unsigned); it is flipped here so a deficit is negative throughout the
    # repo, the way the chart code and every other series expect.
    ytd = budget_rows()
    print(f"  [mts] {len(ytd)} fiscal years")
    rows = []
    for fy in range(FY_FROM, FY_TO + 1):
        r = ytd.get(fy)
        g, nq = gdp.get(fy, (None, 0))
        rcpt = num(r["current_month_gross_rcpt_amt"]) if r else None
        outly = num(r["current_month_gross_outly_amt"]) if r else None
        dfct = num(r["current_month_dfct_sur_amt"]) if r else None
        surplus = None if dfct is None else -dfct
        pc = (lambda v: "" if (v is None or not g) else f"{v / 1e6 / g * 100:.2f}")
        bn = (lambda v: "" if v is None else f"{v / 1e9:.1f}")
        rows.append(f"{fy},{bn(rcpt)},{bn(outly)},{bn(surplus)},"
                    f"{pc(rcpt)},{pc(outly)},{pc(surplus)},"
                    f"{'' if g is None else f'{g / 1000:.1f}'},{nq}")
    (DATA / "fiscal" / "budget_from_api.csv").write_text(
        "fiscal_year,receipts,outlays,deficit,receipts_pct_gdp,"
        "outlays_pct_gdp,deficit_pct_gdp,fy_gdp,gdp_quarters\n"
        + "\n".join(rows) + "\n")
    print("  -> data/fiscal/budget_from_api.csv")

    # ---- the debt, at each fiscal year end -------------------------------
    # 30 September is not always a business day, so the nearest preceding
    # published date is used and the CSV records which one it was.
    # Only each September is fetched: the full daily series is ~5,000 rows
    # per decade and nothing here needs a day that is not a year end.
    by_date: dict[str, dict] = {}
    for fy in range(FY_FROM, FY_TO + 1):
        got = get("/v2/accounting/od/debt_to_penny",
                  {"filter": f"record_date:gte:{fy}-09-01,"
                             f"record_date:lte:{fy}-09-30",
                   "page[size]": 100, "sort": "record_date"},
                  f"debt_to_penny_{fy}_09")
        by_date.update({r["record_date"]: r for r in got})
    print(f"  [debt] {len(by_date)} September records")
    rows = []
    for fy in range(FY_FROM, FY_TO + 1):
        asof = max((d for d in by_date
                    if d <= f"{fy}-09-30" and d >= f"{fy}-09-01"), default=None)
        if asof is None:
            rows.append(f"{fy},,,,,")
            continue
        r = by_date[asof]
        gross = num(r["tot_pub_debt_out_amt"])
        public = num(r["debt_held_public_amt"])
        g, _ = gdp.get(fy, (None, 0))
        pc = (lambda v: "" if (v is None or not g) else f"{v / 1e6 / g * 100:.2f}")
        tn = (lambda v: "" if v is None else f"{v / 1e12:.3f}")
        rows.append(f"{fy},{tn(gross)},{tn(public)},{pc(gross)},{pc(public)},{asof}")
    (DATA / "fiscal" / "debt_from_api.csv").write_text(
        "fiscal_year,gross_tn,public_tn,gross_pct_gdp,public_pct_gdp,asof\n"
        + "\n".join(rows) + "\n")
    print("  -> data/fiscal/debt_from_api.csv")
    print("Done.")


if __name__ == "__main__":
    main()
