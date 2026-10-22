#!/usr/bin/env python3
"""Refresh the ADB Key Indicators (KIDB) series for Vietnam into sidecars.

Usage:  python3 -I countries/vietnam/fetch/fetch_adb.py [--refresh]

KIDB sits behind an SDMX v5 API that is not documented in HTML (the doc
page is JavaScript; the routes come from kidb.adb.org/js/web.js):

    https://kidb.adb.org/api/v5/sdmx/data/ADB,<DF>/A..VIE?format=sdmx-csv
    https://kidb.adb.org/api/v5/sdmx/structure/codelist/all/all/+

The economy code is VIE, not VNM. data.adb.org is behind Cloudflare and is
not used. Every series here is official: false: ADB is a redistributor
(DATA_SOURCE names the NSO, the SBV or the MOF for most rows).

Things this source will mislead you about.

**UNIT_MULT is per series.** OBS_VALUE is in 10**UNIT_MULT units: VND
levels come at 9 (bn VND), USD at 6 (mn USD), persons at 6 (mn), GDP per
capita in VND at 3. Every value is rescaled from the row's own UNIT_MULT
to the unit the column names, so an edition that changes the multiplier
changes nothing in the sidecar. UNIT is asserted per column.

**FOOTNOTE is series-level and query-dependent.** KIDB attaches one
footnote to every row of a series and prefixes it with the span of the
QUERY ("2005-2010: ..." when startPeriod=2005, "2008-2010: ..." when it is
2008), so the prefix says nothing about which years the note covers. The
footnotes are carried verbatim, one per column, in the CSV comments.

**The 2010 GDP-scale break is inside one KIDB series.** NGDP_XDC runs on
the old (unreevaluated) scale to 2009 and on the NSO's 2019-revalued scale
from 2010, flagged OBS_STATUS B at 2010. In gdp_from_adb.csv every level
and every %-of-GDP share is split into *_old_scale (<= 2009) and
*_new_scale (>= 2010) columns that never overlap. Growth rates are
within-scale ratios and stay single, with the break in break_flags.
Elsewhere (fiscal, money, BoP %GDP) the denominator break is named in the
comments.

**OBS_STATUS** is kept: every non-"A" status (B = time-series break) is
listed in each sidecar's break_flags column as column:STATUS. A sidecar
with no flagged observation carries no break_flags column at all.

Cache: countries/vietnam/cache/adb_<DF>.csv and adb_codelists.xml, reused
unless --refresh is given. Outputs are `_from_adb.csv` sidecars.
"""
from __future__ import annotations

import csv
import io
import sys
import time
import unicodedata
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache"

API = "https://kidb.adb.org/api/v5/sdmx"
DATA_URL = API + "/data/ADB,{df}/A..VIE?format=sdmx-csv&startPeriod={y0}"
CODELIST_URL = API + "/structure/codelist/all/all/+"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) worldreports-fetch"}
GAP = 2.0
Y0 = 2005
SCALE_BREAK = 2010     # first year on the NSO's revalued GDP scale

HEAD = ["DATAFLOW", "FREQ", "INDICATOR", "ECONOMY_CODE", "TIME_PERIOD",
        "OBS_VALUE", "UNIT", "UNIT_MULT"]
SDMX = "{http://www.sdmx.org/resources/sdmxml/schemas/v3_0/structure}"
COMMON = "{http://www.sdmx.org/resources/sdmxml/schemas/v3_0/common}"

REFRESH = "--refresh" in sys.argv[1:]
_last = [0.0]

# (dataflow, indicator, column, expected UNIT, target exponent, split?)
# Target exponent: 9 = bn, 6 = mn, 3 = thousand, 0 = as published (rates).
GDP = [
    ("DF_NA", "NGDP_XDC", "gdp_bn_vnd", "VND", 9, True),
    ("DF_NA", "NGDE_XDC", "gdp_expenditure_bn_vnd", "VND", 9, True),
    ("DF_NA", "NGDP_R_XDC", "gdp_real_bn_vnd", "VND", 9, True),
    ("DF_NA", "NC_HFC_XDC_PS", "household_consumption_bn_vnd", "VND", 9, True),
    ("DF_NA", "NCGG_XDC", "government_consumption_bn_vnd", "VND", 9, True),
    ("DF_NA", "NI_XDC", "gross_capital_formation_bn_vnd", "VND", 9, True),
    ("DF_NA", "NFI_XDC_PS", "gross_fixed_capital_formation_bn_vnd", "VND", 9, True),
    ("DF_NA", "NEGS_XDC_PS", "exports_gs_bn_vnd", "VND", 9, True),
    ("DF_NA", "NIGS_XDC_PS", "imports_gs_bn_vnd", "VND", 9, True),
    ("DF_NA", "NYG_XDC", "gni_bn_vnd", "VND", 9, True),
    ("DF_NA", "NGDPPC_XDC", "gdp_per_capita_th_vnd", "VND", 3, True),
    ("DF_NA", "NY_GDP_MKTP_CD", "gdp_mn_usd", "USD", 6, True),
    ("DF_NA", "NY_GDP_PCAP_CD", "gdp_per_capita_usd", "USD", 0, True),
    ("DF_NA", "NC_HFC_XGDP_PS", "household_consumption_pct_gdp", "PCT", 0, True),
    ("DF_NA", "NCGG_XGDP_PS", "government_consumption_pct_gdp", "PCT", 0, True),
    ("DF_NA", "NI_XGDP_PS", "gross_capital_formation_pct_gdp", "PCT", 0, True),
    ("DF_NA", "NEGS_XGDP_PS", "exports_gs_pct_gdp", "PCT", 0, True),
    ("DF_NA", "NIGS_XGDP_PS", "imports_gs_pct_gdp", "PCT", 0, True),
    ("DF_NA", "NIF_GDS_XGDP_PS", "gross_domestic_saving_pct_gdp", "PCT", 0, True),
    ("DF_NA", "NGDPSO_AGR_XGDP_PS", "agriculture_share_pct", "PCT", 0, True),
    ("DF_NA", "NGDPSO_IND_XGDP_PS", "industry_share_pct", "PCT", 0, True),
    ("DF_NA", "NGDPSO_SER_XGDP_PS", "services_share_pct", "PCT", 0, True),
    ("DF_NA", "NGDP_R_PTX_PS", "gdp_real_growth_pct", "PCT", 0, False),
    ("DF_NA", "NGDP_PC_R_PTX_RT_PS", "gdp_per_capita_real_growth_pct", "PCT", 0, False),
    ("DF_NA", "NC_HFC_PTX_PS", "household_consumption_real_growth_pct", "PCT", 0, False),
    ("DF_NA", "NI_PTX_PS", "gross_capital_formation_real_growth_pct", "PCT", 0, False),
    ("DF_NA", "NEGS_PTX_PS", "exports_gs_real_growth_pct", "PCT", 0, False),
    ("DF_NA", "NIGS_PTX_PS", "imports_gs_real_growth_pct", "PCT", 0, False),
    ("DF_NA", "NGDPVA_IND_R_PTX_PS", "industry_real_growth_pct", "PCT", 0, False),
    ("DF_NA", "NGDPVA_SER_R_PTX_PS", "services_real_growth_pct", "PCT", 0, False),
]
GG = [
    ("DF_GOV_FIN", "GR_G14_GG_XDC", "revenue_bn_vnd", "VND", 9, False),
    ("DF_GOV_FIN", "GRT_G14_GG_XDC", "tax_revenue_bn_vnd", "VND", 9, False),
    ("DF_GOV_FIN", "GRTI_G14_GG_XDC", "taxes_income_profits_bn_vnd", "VND", 9, False),
    ("DF_GOV_FIN", "GRTGS_G14_GG_XDC", "taxes_goods_services_bn_vnd", "VND", 9, False),
    ("DF_GOV_FIN", "GRTT_G14_GG_XDC", "taxes_international_trade_bn_vnd", "VND", 9, False),
    ("DF_GOV_FIN", "GRG_G14_GG_XDC", "grants_bn_vnd", "VND", 9, False),
    ("DF_GOV_FIN", "GRO_G14_GG_XDC", "other_revenue_bn_vnd", "VND", 9, False),
    ("DF_GOV_FIN", "GE_G14_GG_XDC", "expense_bn_vnd", "VND", 9, False),
    ("DF_GOV_FIN", "GEI_G14_GG_XDC", "interest_bn_vnd", "VND", 9, False),
    ("DF_GOV_FIN", "GADAN_T_G14_GG_XDC", "net_investment_nonfinancial_assets_bn_vnd", "VND", 9, False),
    ("DF_GOV_FIN", "GX_G14_GG_XDC", "expenditure_bn_vnd", "VND", 9, False),
    ("DF_GOV_FIN", "GXCBN_G14_GG_XDC", "net_operating_balance_bn_vnd", "VND", 9, False),
    ("DF_GOV_FIN", "GXCNL_G14_GG_XDC", "net_lending_bn_vnd", "VND", 9, False),
    ("DF_GOV_FIN", "GXOPB_G14_GG_XDC", "primary_balance_bn_vnd", "VND", 9, False),
    ("DF_GOV_FIN", "GR_G14_GG_XGDP_PS", "revenue_pct_gdp", "PCT", 0, False),
    ("DF_GOV_FIN", "GRT_G14_GG_XGDP_PS", "tax_revenue_pct_gdp", "PCT", 0, False),
    ("DF_GOV_FIN", "GX_G14_GG_XGDP_PS", "expenditure_pct_gdp", "PCT", 0, False),
    ("DF_GOV_FIN", "GXCNL_G14_GG_XGDP_PS", "net_lending_pct_gdp", "PCT", 0, False),
    ("DF_GOV_FIN", "GXOPB_G14_GG_XGDP_PS", "primary_balance_pct_gdp", "PCT", 0, False),
]
LFE = [
    ("DF_LFE", "LUR_PT", "unemployment_rate_pct", "PCT", 0, False),
    ("DF_LFE", "LLF_PE_NUM", "labour_force_mn", "PERSONS", 6, False),
    ("DF_LFE", "LE_PE_NUM", "employed_mn", "PERSONS", 6, False),
    ("DF_LFE", "LU_PE_NUM", "unemployed_mn", "PERSONS", 6, False),
    ("DF_LFE", "LUD_PE_NUM_PS", "underemployed_mn", "PERSONS", 6, False),
    ("DF_LFE", "LPR_RATE", "participation_rate_pct", "PCT", 0, False),
    ("DF_LFE", "LPR_RATE_M_PS", "participation_rate_male_pct", "PCT", 0, False),
    ("DF_LFE", "LPR_RATE_F_PS", "participation_rate_female_pct", "PCT", 0, False),
] + [
    ("DF_LFE", f"LE_PE_NUM_{s}_PS", f"employed_{s.lower()}_mn", "PERSONS", 6, False)
    for s in ("A", "B", "C", "D", "F", "G", "H", "I", "J", "K", "L", "OT")
]
BOP_CODES = [
    ("BCA", "current_account"), ("BG", "goods_balance"), ("BXG", "goods_exports"),
    ("BMG", "goods_imports"), ("BS", "services_balance"), ("BXS", "services_credit"),
    ("BMS", "services_debit"), ("BIP", "primary_income_balance"),
    ("BXIP", "primary_income_credit"), ("BMIP", "primary_income_debit"),
    ("BIS", "secondary_income_balance"), ("BXIS", "secondary_income_credit"),
    ("BMIS", "secondary_income_debit"), ("BK", "capital_account"),
    ("BF", "financial_account"), ("BFD", "direct_investment"),
    ("BFP", "portfolio_investment"), ("BFO", "other_investment"),
    ("BOP", "net_errors_omissions"), ("BO", "overall_balance"),
    ("BTRUE", "reserves_related_items"),
]
BOP = [
    ("DF_GLOB_BOP", (f"{c}_BP6_FY_USD" if c in ("BO", "BTRUE") else f"{c}_BP6_USD"),
     f"{name}_mn_usd", "USD", 6, False) for c, name in BOP_CODES
] + [
    ("DF_GLOB_BOP", "BCA_BP6_XGDP_PS", "current_account_pct_gdp", "PCT", 0, False),
    ("DF_GLOB_BOP", "BG_BP6_XGDP_PS", "goods_balance_pct_gdp", "PCT", 0, False),
    ("DF_GLOB_BOP", "BOP_BAL_ON_SVC", "services_balance_pct_gdp", "PCT", 0, False),
    ("DF_GLOB_BOP", "BO_BP6_FY_XGDP_PS", "overall_balance_pct_gdp", "PCT", 0, False),
]
CREDIT = [
    ("DF_MF_MON", "FMIR_DC_CPS_XDC_PS", "claims_private_sector_bn_vnd", "VND", 9, False),
    ("DF_MF_MON", "FMIR_DC_XDC_PS", "domestic_claims_bn_vnd", "VND", 9, False),
    ("DF_MF_MON", "FMIR_DC_CCG_XDC_PS", "claims_central_government_net_bn_vnd", "VND", 9, False),
    ("DF_MF_MON", "FMIR_BM_M2_XDC_PS", "m2_bn_vnd", "VND", 9, False),
    ("DF_MF_MON", "FMN_XDC", "m1_bn_vnd", "VND", 9, False),
    ("DF_MF_MON", "FM2_XGDP_PS", "m2_pct_gdp", "PCT", 0, False),
    ("DF_MF_MON", "FM2_PTX_PS", "m2_growth_pct", "PCT", 0, False),
    ("DF_MF_MON", "FMIR_OD_T12_XPA_PS", "deposit_rate_12m_pct", "PCT", 0, False),
    ("DF_MF_FIN", "FSANL_PT", "npl_ratio_pct", "PCT", 0, False),
]
REMIT = [
    ("DF_GLOB_BOP", "BXIS_BP6_USD", "secondary_income_credit_mn_usd", "USD", 6, False),
]

# Spot values recorded in DISCOVERY.md / SOURCES.yaml on 2026-10-22, plus
# second-source magnitudes: (file, column, year, want, tolerance, origin).
CHECKS = [
    ("gdp", "gdp_expenditure_bn_vnd_old_scale", 2006, 1061565, 1, "ADB"),
    ("gdp", "gdp_bn_vnd_old_scale", 2009, 1809149, 1, "NSO V03.01 (old scale)"),
    ("gdp", "gdp_bn_vnd_new_scale", 2010, 2739843, 1, "NSO V03.01 (new scale)"),
    ("gdp", "gdp_real_growth_pct", 2008, 5.66, 0.006, "ADB/NSO"),
    ("gdp", "gdp_real_growth_pct", 2009, 5.40, 0.006, "ADB/NSO"),
    ("gdp", "gdp_mn_usd_new_scale", 2024, 476300, 500, "World Bank NY.GDP.MKTP.CD"),
    ("gdp", "gdp_mn_usd_new_scale", 2010, 147200, 500, "World Bank NY.GDP.MKTP.CD"),
    ("gg", "revenue_bn_vnd", 2006, 262063, 1, "ADB"),
    ("gg", "revenue_pct_gdp", 2006, 24.7, 0.06, "ADB"),
    ("gg", "tax_revenue_pct_gdp", 2006, 21.9, 0.06, "ADB"),
    ("gg", "net_lending_pct_gdp", 2006, 0.25, 0.006, "ADB"),
    ("lfe", "unemployment_rate_pct", 2006, 4.88, 0.006, "ADB/NSO LFS"),
    ("lfe", "unemployment_rate_pct", 2024, 2.24, 0.006, "ADB/NSO LFS"),
    ("lfe", "unemployment_rate_pct", 2025, 2.21, 0.006, "ADB/NSO LFS"),
    ("bop", "current_account_mn_usd", 2024, 30384.568, 0.01, "NSO V03.20"),
    ("bop", "secondary_income_credit_mn_usd", 2024, 16998, 1, "ADB"),
    ("credit", "claims_private_sector_bn_vnd", 2006, 693834, 1, "ADB/SBV"),
    ("credit", "claims_private_sector_bn_vnd", 2024, 15705613, 1, "ADB/SBV"),
    ("credit", "m2_pct_gdp", 2006, 86.9, 0.06, "ADB"),
    ("credit", "m2_pct_gdp", 2024, 155.6, 0.06, "ADB"),
    ("credit", "npl_ratio_pct", 2024, 4.85, 0.006, "ADB/IMF FSI"),
    ("remit", "secondary_income_credit_mn_usd", 2025, 19800, 100, "ADB"),
]


def _get(url: str) -> bytes:
    last = None
    for attempt in range(4):
        wait = _last[0] + GAP - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=180) as r:
                body = r.read()
            _last[0] = time.monotonic()
            return body
        except urllib.error.HTTPError as e:
            _last[0] = time.monotonic()
            last = e
            if e.code in (403, 429, 500, 502, 503):
                time.sleep(20 * (attempt + 1))
                continue
            raise RuntimeError(f"{url}: HTTP {e.code}") from e
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            _last[0] = time.monotonic()
            last = e
            time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"{url}: {last}")


def dataflow(df: str) -> list[dict]:
    """The VIE rows of one KIDB dataflow, shape-checked before caching."""
    CACHE.mkdir(exist_ok=True)
    path = CACHE / f"adb_{df}.csv"
    if path.exists() and not REFRESH:
        text = path.read_text(encoding="utf-8")
    else:
        body = _get(DATA_URL.format(df=df, y0=Y0))
        text = body.decode("utf-8-sig")
        head = next(csv.reader(io.StringIO(text)), [])
        if head[:len(HEAD)] != HEAD or "FOOTNOTE" not in head:
            raise SystemExit(f"  !! {df}: not an SDMX-CSV payload "
                             f"(header {head[:6]!r}, {text[:80]!r})")
        rows = list(csv.DictReader(io.StringIO(text)))
        if not rows:
            raise SystemExit(f"  !! {df}: empty reply")
        bad = {r["ECONOMY_CODE"] for r in rows} - {"VIE"}
        if bad:
            raise SystemExit(f"  !! {df}: rows for other economies {bad}")
        path.write_text(text, encoding="utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def labels() -> dict[str, str]:
    """Indicator code -> English name, from CL_KIDB_INDICATORS."""
    path = CACHE / "adb_codelists.xml"
    if path.exists() and not REFRESH:
        body = path.read_bytes()
    else:
        body = _get(CODELIST_URL)
        if b"CL_KIDB_INDICATORS" not in body or not body.lstrip().startswith(b"<?xml"):
            raise SystemExit("  !! codelists: CL_KIDB_INDICATORS not in reply")
        path.write_bytes(body)
    out = {}
    for cl in ET.fromstring(body).iter(SDMX + "Codelist"):
        if cl.get("id") == "CL_KIDB_INDICATORS":
            for c in cl.findall(SDMX + "Code"):
                name = c.find(COMMON + "Name")
                out[c.get("id")] = unicodedata.normalize("NFC", name.text or "")
    if not out:
        raise SystemExit("  !! codelists: CL_KIDB_INDICATORS is empty")
    return out


def scaled(obs: str, mult: str, target: int) -> str:
    """OBS_VALUE x 10**(UNIT_MULT - target), as a plain decimal string."""
    d = Decimal(obs).scaleb(int(mult or 0) - target)
    s = format(d.normalize(), "f")
    return "0" if s in ("-0", "") else s


def build(spec, flows, names):
    """{year: {col: value}}, {year: [flags]}, [comment lines], [columns]."""
    table: dict[int, dict[str, str]] = {}
    flags: dict[int, list[str]] = {}
    notes, columns = [], []
    for df, code, col, unit, target, split in spec:
        rows = [r for r in flows[df] if r["INDICATOR"] == code]
        if not rows:
            raise SystemExit(f"  !! {df} {code}: no rows")
        units = {r["UNIT"] for r in rows}
        if units != {unit}:
            raise SystemExit(f"  !! {df} {code}: UNIT {units}, expected {unit}")
        mults = sorted({r["UNIT_MULT"] for r in rows})
        cols = ([f"{col}_old_scale", f"{col}_new_scale"] if split else [col])
        columns += cols
        r0 = rows[0]
        meta = [f"UNIT {unit}, UNIT_MULT {'/'.join(mults)} rescaled to 10^{target}"]
        for key in ("REF_YEAR", "BASE_YEAR", "DATA_SOURCE"):
            if r0.get(key):
                meta.append(f"{key} {r0[key]}")
        notes.append(f"# {', '.join(cols)}: {code} \"{names.get(code, '?')}\" "
                     f"({'; '.join(meta)})")
        foots = {unicodedata.normalize("NFC", r["FOOTNOTE"]) for r in rows if r["FOOTNOTE"]}
        for f in sorted(foots):
            notes.append(f"#   FOOTNOTE: {' '.join(f.split())}")
        for r in rows:
            y = int(r["TIME_PERIOD"])
            if r["OBS_VALUE"] == "":
                continue
            c = cols[0] if not split else cols[0 if y < SCALE_BREAK else 1]
            table.setdefault(y, {})[c] = scaled(r["OBS_VALUE"], r["UNIT_MULT"], target)
            if r.get("OBS_STATUS") and r["OBS_STATUS"] != "A":
                flags.setdefault(y, []).append(f"{col}:{r['OBS_STATUS']}")
    return table, flags, notes, columns


def write(rel: str, preface: list[str], spec, flows, names) -> dict:
    table, flags, notes, columns = build(spec, flows, names)
    years = sorted(table)
    lines = ["# official: false. Asian Development Bank, Key Indicators Database "
             "(kidb.adb.org SDMX v5, economy VIE), a redistributor."]
    lines += [f"# {p}" for p in preface]
    # An all-blank break_flags column fails the shared data tests (a column
    # of blanks promises data that is not there), so it is written only when
    # some observation carries a non-normal OBS_STATUS.
    flagged = any(flags.values())
    if flagged:
        lines += ["# break_flags lists column:OBS_STATUS for every non-normal "
                  "observation (B = time-series break). Blank = not published."]
    else:
        lines += ["# No observation carries a non-normal OBS_STATUS, so there "
                  "is no break_flags column. Blank = not published."]
    lines += notes
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(["year"] + columns + (["break_flags"] if flagged else []))
    for y in range(years[0], years[-1] + 1):
        row = table.get(y, {})
        w.writerow([y] + [row.get(c, "") for c in columns]
                   + ([";".join(sorted(set(flags.get(y, []))))] if flagged else []))
    path = DATA / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n" + out.getvalue(), encoding="utf-8")
    print(f"  -> data/{rel} ({len(range(years[0], years[-1] + 1))} rows, "
          f"{years[0]}–{years[-1]}, {len(columns)} columns)")
    return table


def verify(tables: dict[str, dict]) -> None:
    for key, col, year, want, tol, origin in CHECKS:
        got = tables[key].get(year, {}).get(col)
        if got in (None, ""):
            raise SystemExit(f"  !! {key}.{col} {year}: missing (want {want}, {origin})")
        if abs(float(got) - want) > tol:
            raise SystemExit(f"  !! {key}.{col} {year} = {got}, want {want} "
                             f"± {tol} ({origin})")
        print(f"  ok {key}.{col} {year} = {float(got):,.3f} ({origin})")
    # The scale split must be clean: no year on both sides, and ADB still
    # flags the break exactly at 2010.
    gdp = tables["gdp"]
    for y, row in gdp.items():
        if y < SCALE_BREAK and any(k.endswith("_new_scale") for k in row):
            raise SystemExit(f"  !! gdp {y}: new-scale value before {SCALE_BREAK}")
        if y >= SCALE_BREAK and any(k.endswith("_old_scale") for k in row):
            raise SystemExit(f"  !! gdp {y}: old-scale value from {SCALE_BREAK}")
    gg_last = max(tables["gg"])
    if gg_last < 2022:
        raise SystemExit(f"  !! gg finance ends {gg_last}, manifest says 2022")
    if gg_last > 2022:
        print(f"  note: gg finance now runs to {gg_last} (manifest says 2022)")


def main() -> None:
    print("Fetching ADB KIDB (economy VIE)...")
    names = labels()
    flows = {df: dataflow(df) for df in
             ("DF_NA", "DF_GOV_FIN", "DF_LFE", "DF_GLOB_BOP", "DF_MF_MON", "DF_MF_FIN")}
    na_break = {r["TIME_PERIOD"] for r in flows["DF_NA"]
                if r["INDICATOR"] == "NGDP_XDC" and r["OBS_STATUS"] == "B"}
    if na_break != {str(SCALE_BREAK)}:
        raise SystemExit(f"  !! NGDP_XDC break flagged at {na_break}, expected 2010")
    tables = {}
    tables["gdp"] = write("macro/gdp_from_adb.csv", [
        "National accounts republished from the NSO, calendar years.",
        "GDP SCALE BREAK: *_old_scale columns are the NSO's unreevaluated scale",
        "(years <= 2009); *_new_scale columns are the 2019-revalued scale (2010+).",
        "They are different measurements and must never be joined into one line.",
        "Growth rates are within-scale and are single columns (2010 flagged B).",
        "Constant-price levels are at 2010 prices (BASE_YEAR); ADB flags a break",
        "in the constant-price series at 2005 as well.",
    ], GDP, flows, names)
    tables["gg"] = write("fiscal/gg_finance_from_adb.csv", [
        "General government, GFSM 2014 (MOF via ADB). Keyed on the calendar year:",
        "Vietnam's budget year is January–December (REF_YEAR 'Ending 31 December').",
        "A different concept from the NSO's state-budget (cash) tables; never spliced.",
        "%-of-GDP ratios before 2010 use the OLD GDP scale as denominator, so they",
        "read higher than they would on the revalued scale.",
    ], GG, flows, names)
    tables["lfe"] = write("social/unemployment_from_adb.csv", [
        "Labour force survey (NSO via ADB). Unemployment rate is ages 15+, a",
        "different age base from the NSO's working-age rate: its own line.",
        "Definitional break 2020->2021 (ICLS 13 -> ICLS 19, flagged B in 2021);",
        "see the footnotes. Persons in millions.",
    ], LFE, flows, names)
    tables["bop"] = write("international/bop_from_adb.csv", [
        "Balance of payments (SBV via ADB), USD mn, calendar years. BPM5 before",
        "2014, BPM6 from 2014 (flagged B). Financial-account sign convention is",
        "ADB's as published. %-of-GDP before 2010 uses the old GDP scale.",
    ], BOP, flows, names)
    tables["credit"] = write("credit/credit_from_adb.csv", [
        "Depository-corporations survey (SBV via ADB), end of period, bn VND;",
        "NPL ratio is the IMF-FSI-reported figure, not the SBV's own 'tỷ lệ nợ xấu'.",
        "M2 % of GDP before 2010 uses the OLD GDP scale as denominator.",
    ], CREDIT, flows, names)
    tables["remit"] = write("migration/remittances_proxy_from_adb.csv", [
        "Secondary income, CREDIT, USD mn (BPM5 to 2013, BPM6 from 2014, flagged B):",
        "a SUPERSET of remittances (it includes other current transfers). Label it",
        "'secondary income received (includes remittances)', never 'remittances'.",
        "Same rows as bop_from_adb; the NSO's V03.20 2018+ rows equal them.",
    ], REMIT, flows, names)
    verify(tables)
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
