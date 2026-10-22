#!/usr/bin/env python3
"""Fetch mortality from the CDC: violence, overdoses, COVID-19 and influenza.

Three CDC sources, all key-free, all counting death certificates filed under
the National Vital Statistics System:

  WONDER, Underlying Cause of Death 1999-2020 (database D76). The final file.
  Queried by ICD-10 code over a POST of XML form parameters. WONDER enforces
  15 seconds between requests, so every answer is cached.

  "Mapping Injury, Overdose, and Violence - National" (Socrata t6u2-f84c),
  which carries the same measures for 2019 onward, provisionally. It overlaps
  the final file on 2019 and 2020, so the join is checked rather than assumed
  — `make update` prints the two side by side.

  "Provisional COVID-19 Death Counts by Week Ending Date and State"
  (Socrata r8kw-7aab), which is the only table that reports COVID-19,
  influenza, pneumonia and all-cause deaths on one consistent basis.

Two caveats travel with these numbers and are annotated on the plates:

  * Influenza deaths here are death-certificate counts (J09-J11) and badly
    understate influenza mortality. CDC's own modelled burden estimates run
    several times higher, because most flu deaths are certified as pneumonia
    or as the chronic condition the infection decompensated. The certificate
    count is the right comparison against the certificate count for COVID-19,
    and the wrong one against a modelled estimate of either.

  * Deaths from police intervention (Y35) are undercounted for a structural
    reason: the ICD code follows what the certifier wrote, and studies that
    match certificates against news and court records find roughly half of
    these deaths certified as ordinary homicides instead.

Outputs:
  data/social/mortality.csv  year,covid,influenza,pneumonia,total_deaths,weeks
  data/social/violence.csv   year,homicides_final,homicide_rate_final,
                             homicides_prov,homicide_rate_prov,
                             firearm_homicides,firearm_deaths,
                             firearm_suicides,suicides,overdoses,...
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "cdc"
DATA = ROOT / "data"
CACHE.mkdir(parents=True, exist_ok=True)

WONDER = "https://wonder.cdc.gov/controller/datarequest/D76"
SOCRATA = "https://data.cdc.gov/resource/{id}.json"
WONDER_GAP = 16  # seconds; the API rejects anything faster

YEAR_FROM, YEAR_TO = 2006, 2026

# ICD-10 code sets, each the standard definition for its measure.
#
# WONDER's "ICD-10 Codes" selector takes one <value> per selection, and a
# range is only accepted when it is a node of its own hierarchy: "X85-Y09"
# (the Assault block) and "X60-X84" (Intentional self-harm) are nodes, while
# "X93-X95" is three codes inside a block and has to be named one at a time.
# `expand` turns the second kind into its members so the definitions below
# can stay written the way the literature writes them.
CAUSES: dict[str, tuple[str, ...]] = {
    "homicides": ("X85-Y09",),
    "firearm_homicides": ("X93", "X94", "X95"),
    "firearm_deaths": ("W32", "W33", "W34", "X72", "X73", "X74",
                       "X93", "X94", "X95", "Y22", "Y23", "Y24", "Y35.0"),
    "police_killings": ("Y35",),
    "suicides": ("X60-X84", "Y87.0"),
    "overdoses": ("X40", "X41", "X42", "X43", "X44",
                  "X60", "X61", "X62", "X63", "X64", "X85",
                  "Y10", "Y11", "Y12", "Y13", "Y14"),
}

# The respiratory-disease and all-cause series, kept apart from CAUSES
# because they answer a different question and are joined to a different
# provisional file. "*All*" is WONDER's own selector for every cause, which
# is how all-cause mortality is asked for rather than by listing ICD-10.
HEALTH: dict[str, tuple[str, ...]] = {
    "influenza": ("J09", "J10", "J11"),
    # J17, pneumonia in diseases classified elsewhere, is deliberately
    # absent: it can never be an underlying cause, so WONDER rejects it
    # outright rather than returning zero.
    "pneumonia": ("J12", "J13", "J14", "J15", "J16", "J18"),
    "all_cause": ("*All*",),
    # 2020 only, and fetched purely to test the join: WONDER counts the
    # UNDERLYING cause, while the provisional file counts deaths that
    # INVOLVED COVID-19. If the two disagree materially then the series
    # cannot be joined and the pre-2020 years have to stay empty.
    "covid_underlying": ("U07.1",),
}


# ---------------------------------------------------------------- WONDER
def _param(name: str, *values: str) -> str:
    vals = "".join(f"<value>{v}</value>" for v in values)
    return f"<parameter><name>{name}</name>{vals}</parameter>"


def wonder_request(codes: tuple[str, ...]) -> str:
    """The full D76 form. WONDER validates every field, not just the ones
    that matter, so each byvariable and filter is present even when unused."""
    params = [
        _param("accept_datause_restrictions", "true"),
        _param("B_1", "D76.V1-level1"), _param("B_2", "*None*"),
        _param("B_3", "*None*"), _param("B_4", "*None*"),
        _param("B_5", "*None*"),
        _param("M_1", "D76.M1"), _param("M_2", "D76.M2"),
        _param("M_3", "D76.M3"),
        _param("F_D76.V1", "*All*"), _param("F_D76.V2", *codes),
        _param("F_D76.V9", "*All*"), _param("F_D76.V10", "*All*"),
        _param("F_D76.V27", "*All*"),
        _param("I_D76.V1", "*All* (All Dates)"),
        _param("I_D76.V2", "*All* (All Causes of Death)"),
        _param("V_D76.V1", ""), _param("V_D76.V2", ""),
        _param("V_D76.V4", "*All*"), _param("V_D76.V5", "*All*"),
        _param("V_D76.V6", "00"), _param("V_D76.V7", "*All*"),
        _param("V_D76.V8", "*All*"), _param("V_D76.V9", ""),
        _param("V_D76.V10", ""), _param("V_D76.V11", "*All*"),
        _param("V_D76.V12", "*All*"), _param("V_D76.V17", "*All*"),
        _param("V_D76.V19", "*All*"), _param("V_D76.V20", "*All*"),
        _param("V_D76.V21", "*All*"), _param("V_D76.V22", "*All*"),
        _param("V_D76.V23", "*All*"), _param("V_D76.V24", "*All*"),
        _param("V_D76.V25", "*All*"), _param("V_D76.V27", ""),
        _param("O_V1_fmode", "freg"), _param("O_V2_fmode", "freg"),
        _param("O_V9_fmode", "freg"), _param("O_V10_fmode", "freg"),
        _param("O_V27_fmode", "freg"),
        _param("O_aar", "aar_none"), _param("O_aar_pop", "0000"),
        _param("O_age", "D76.V5"), _param("O_javascript", "on"),
        _param("O_location", "D76.V9"), _param("O_precision", "1"),
        _param("O_rate_per", "100000"), _param("O_show_totals", "false"),
        _param("O_timeout", "600"), _param("O_title", "annual deaths"),
        _param("O_ucd", "D76.V2"), _param("O_urban", "D76.V19"),
        _param("VM_D76.M6_D1", "*All*"), _param("VM_D76.M6_D2", "*All*"),
        _param("VM_D76.M6_D76.V1_H", "*All*"),
        _param("VM_D76.M6_D76.V7", "*All*"),
        _param("VM_D76.M6_D76.V8", "*All*"),
        _param("VM_D76.M6_D76.V10", ""),
    ]
    return "<request-parameters>" + "".join(params) + "</request-parameters>"


_last_call = [0.0]


def wonder(name: str, codes: tuple[str, ...]) -> dict[int, tuple[float, float]]:
    """{year: (deaths, crude rate per 100k)} for one ICD-10 code set."""
    cache = CACHE / f"wonder_{name}.json"
    if cache.exists():
        raw = json.loads(cache.read_text())
        return {int(y): tuple(v) for y, v in raw.items()}

    wait = WONDER_GAP - (time.time() - _last_call[0])
    if wait > 0:
        time.sleep(wait)
    print(f"  [wonder] {name}: {' '.join(codes)}")
    try:
        r = requests.post(WONDER, data={"request_xml": wonder_request(codes)},
                          timeout=600)
        _last_call[0] = time.time()
        # WONDER returns <message> for notices as well as for errors — a
        # query spanning years with no deaths answers correctly and then
        # remarks that zero rows are hidden. Treating any message as a
        # failure threw away good data, so the table decides: a response
        # with data rows is a success whatever it also says.
        notes = [" ".join(m.split())[:200] for m in
                 re.findall(r"<message>(.*?)</message>", r.text, flags=re.S)]
        if notes and "<r>" not in r.text:
            raise ValueError(notes[0])
        for note in notes:
            print(f"     note: {note}")
    except Exception as e:  # noqa: BLE001
        print(f"  !! {name} failed: {type(e).__name__}: {e}")
        return {}

    # The response is a table of <c> cells: each data row is the year label
    # then deaths, population and crude rate. Rows with a suppressed count
    # carry "Suppressed" rather than a number and are dropped.
    out: dict[int, tuple[float, float]] = {}
    for row in re.findall(r"<r>(.*?)</r>", r.text, flags=re.S):
        cells = re.findall(r'<c (?:l|v)="([^"]*)"', row)
        if len(cells) < 4 or not cells[0].isdigit():
            continue
        try:
            deaths = float(cells[1].replace(",", ""))
            rate = float(cells[3].replace(",", ""))
        except ValueError:
            continue
        out[int(cells[0])] = (deaths, rate)
    cache.write_text(json.dumps({str(k): list(v) for k, v in out.items()}))
    print(f"     {len(out)} years")
    return out


# --------------------------------------------------------------- Socrata
def socrata(dataset: str, name: str, **query) -> list[dict]:
    cache = CACHE / f"socrata_{name}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    try:
        r = requests.get(SOCRATA.format(id=dataset), params=query, timeout=180)
        r.raise_for_status()
        rows = r.json()
        if isinstance(rows, dict):
            raise ValueError(rows.get("message", rows))
    except Exception as e:  # noqa: BLE001
        print(f"  !! {name} failed: {type(e).__name__}: {e}")
        return []
    cache.write_text(json.dumps(rows))
    return rows


def injury_national() -> dict[str, dict[int, tuple[float, float]]]:
    """{intent: {year: (count, rate)}} from the national injury series."""
    rows = socrata("t6u2-f84c", "injury_national",
                   geoid="USA", type="year", **{"$limit": 5000})
    out: dict[str, dict[int, tuple[float, float]]] = {}
    for r in rows:
        intent = r.get("intent")
        period = (r.get("period") or "")[:4]
        if not intent or not period.isdigit():
            continue
        try:
            count = float(r["count"])
            rate = float(r["rate"])
        except (KeyError, TypeError, ValueError):
            continue
        out.setdefault(intent, {})[int(period)] = (count, rate)
    return out


def overdoses() -> dict[int, dict[str, float]]:
    """{year: {measure: deaths}} from the VSRR provisional overdose counts.

    This is CDC's own headline overdose series, reported as a 12-month total
    ending in a given month; the December reading is the calendar year. It is
    used in preference to the national injury dashboard's `Drug_OD`, which
    runs about 5% below CDC's published counts — 100,134 against 106,881 for
    2023 — and so does not join the final file cleanly. VSRR agrees with the
    final file to better than 1% over 2015-2020, which `make update` prints.

    The opioid lines are a SUBSET of the total, not a parallel measure, and
    are named that way wherever they are drawn.
    """
    want = {
        "total": "Number of Drug Overdose Deaths",
        "opioids": "Opioids (T40.0-T40.4,T40.6)",
        "synthetic_opioids": "Synthetic opioids, excl. methadone (T40.4)",
    }
    out: dict[int, dict[str, float]] = {}
    for key, indicator in want.items():
        rows = socrata("xkb8-kh2a", f"vsrr_{key}", state="US",
                       month="December", period="12 month-ending",
                       indicator=indicator,
                       **{"$limit": 100, "$order": "year"})
        for r in rows:
            year = (r.get("year") or "").strip()
            try:
                out.setdefault(int(year), {})[key] = float(r["data_value"])
            except (KeyError, TypeError, ValueError):
                continue
    return out


def covid_influenza() -> dict[int, dict[str, float]]:
    """Annual COVID-19, influenza, pneumonia and all-cause deaths.

    `group` is a reserved word in Socrata's query language, so it has to be
    back-quoted in a $where clause; passing it as a plain filter is rejected
    as a malformed query.
    """
    rows = socrata("r8kw-7aab", "covid_influenza",
                   state="United States",
                   **{"$where": '`group`="By Year"', "$limit": 200})
    out: dict[int, dict[str, float]] = {}
    for r in rows:
        year = (r.get("year") or "").strip()
        if not year.isdigit():
            continue
        got = {}
        for key, field in (("covid", "covid_19_deaths"),
                           ("influenza", "influenza_deaths"),
                           ("pneumonia", "pneumonia_deaths"),
                           ("total_deaths", "total_deaths")):
            try:
                got[key] = float(r[field])
            except (KeyError, TypeError, ValueError):
                pass
        out[int(year)] = got
    return out


def fmt(v: float | None, dec: int = 0) -> str:
    return "" if v is None else f"{v:.{dec}f}"


def main() -> None:
    print("Fetching CDC mortality...")
    final = {name: wonder(name, codes) for name, codes in CAUSES.items()}
    health = {name: wonder(name, codes) for name, codes in HEALTH.items()}
    prov = injury_national()
    print(f"  [socrata] injury intents: {sorted(prov)}")

    # ---- the join between the final and provisional files ---------------
    # Both count the same certificates under the same ICD codes; they differ
    # in vintage. Printing the overlap is what makes the seam auditable
    # instead of a claim.
    od = overdoses()
    for y in (2019, 2020):
        f = final["homicides"].get(y)
        p = prov.get("All_Homicide", {}).get(y)
        if f and p:
            print(f"  overlap {y} homicides: final {f[0]:,.0f} vs "
                  f"provisional {p[0]:,.0f} — {(p[0] / f[0] - 1) * 100:+.1f}%")
    for y in (2015, 2018, 2020):
        f = final["overdoses"].get(y)
        v = od.get(y, {}).get("total")
        if f and v:
            print(f"  overlap {y} overdoses: final {f[0]:,.0f} vs VSRR "
                  f"{v:,.0f} — {(v / f[0] - 1) * 100:+.1f}%")

    # ---- violence and overdoses -----------------------------------------
    cols = ("homicides", "homicide_rate", "firearm_homicides",
            "firearm_deaths", "police_killings", "suicides", "overdoses",
            "opioid_overdoses", "synthetic_opioid_overdoses")
    rows = []
    for y in range(YEAR_FROM, YEAR_TO + 1):
        p_hom = prov.get("All_Homicide", {}).get(y)
        p_fa_hom = prov.get("FA_Homicide", {}).get(y)
        p_fa = prov.get("FA_Deaths", {}).get(y)
        p_sui = prov.get("All_Suicide", {}).get(y)
        vsrr = od.get(y, {})
        # VSRR is CDC's published provisional series and agrees with the
        # final file to under 1%, so it takes over where the final file ends
        p_od = (vsrr["total"], 0.0) if "total" in vsrr else None

        def pick(final_key: str, provisional):
            """The final file where it exists, the provisional file after it.
            Which one a year came from is recorded in the `vintage` column —
            they are the same system, not two different measures, so the
            series is continuous, but the tail is not yet final."""
            f = final[final_key].get(y)
            if f:
                return f, "final"
            return provisional, "provisional"

        hom, vintage = pick("homicides", p_hom)
        fa_hom, _ = pick("firearm_homicides", p_fa_hom)
        fa, _ = pick("firearm_deaths", p_fa)
        sui, _ = pick("suicides", p_sui)
        total_od, _ = pick("overdoses", p_od)
        police = final["police_killings"].get(y)
        rows.append(
            f"{y},{fmt(hom[0]) if hom else ''},{fmt(hom[1], 1) if hom else ''},"
            f"{fmt(fa_hom[0]) if fa_hom else ''},{fmt(fa[0]) if fa else ''},"
            f"{fmt(police[0]) if police else ''},{fmt(sui[0]) if sui else ''},"
            f"{fmt(total_od[0]) if total_od else ''},"
            f"{fmt(vsrr.get('opioids'))},"
            f"{fmt(vsrr.get('synthetic_opioids'))},"
            f"{vintage if hom else ''}")
    (DATA / "social" / "violence.csv").write_text(
        f"year,{','.join(cols)},vintage\n" + "\n".join(rows) + "\n")
    print("  -> data/social/violence.csv")

    # ---- COVID-19, influenza, all-cause ---------------------------------
    # These two files do NOT measure the same thing and are not spliced.
    # WONDER counts the UNDERLYING cause — the one condition that started
    # the chain of events ending in death. The provisional file counts
    # deaths that INVOLVED the condition, anywhere on the certificate.
    # Printing the 2020 overlap is what established that: all-cause agrees
    # to 0.2%, a vintage difference, while COVID is 10% apart, influenza
    # 48% and pneumonia 640% — most pneumonia deaths in 2020 involved
    # pneumonia but were caused by COVID-19. So each measure keeps its own
    # column and its own name, and the plate draws them as two lines whose
    # step at 2020 is visibly a change of definition.
    #
    # The underlying-cause series stops at 2020 because the final file
    # does. WONDER's provisional dataset D176 would extend it, but its
    # request form is built in the browser and is not published as a
    # parameter list, so it is left out rather than guessed at.
    ci = covid_influenza()
    for key, wkey in (("total_deaths", "all_cause"), ("covid", "covid_underlying"),
                      ("influenza", "influenza"), ("pneumonia", "pneumonia")):
        f = health.get(wkey, {}).get(2020)
        p_ = ci.get(2020, {}).get(key)
        if f and p_:
            print(f"  overlap 2020 {key}: underlying {f[0]:,.0f} vs involving "
                  f"{p_:,.0f} — {(p_ / f[0] - 1) * 100:+.1f}%")

    cols = ("covid_underlying", "influenza_underlying", "pneumonia_underlying",
            "covid_involved", "influenza_involved", "pneumonia_involved",
            "total_deaths")
    rows = []
    for y in range(YEAR_FROM, YEAR_TO + 1):
        got = ci.get(y, {})
        # all-cause IS joinable, so it is one continuous column with the
        # vintage recorded; the provisional reading wins where both exist
        total = got.get("total_deaths")
        vintage = "provisional" if total is not None else ""
        if total is None:
            f = health.get("all_cause", {}).get(y)
            total, vintage = (f[0], "final") if f else (None, "")
        under = []
        for wkey in ("covid_underlying", "influenza", "pneumonia"):
            f = health.get(wkey, {}).get(y)
            under.append(fmt(f[0]) if f else "")
        rows.append(f"{y}," + ",".join(
            under + [fmt(got.get(k)) for k in ("covid", "influenza", "pneumonia")]
            + [fmt(total)]) + f",{vintage}")
    (DATA / "social" / "mortality.csv").write_text(
        f"year,{','.join(cols)},total_vintage\n" + "\n".join(rows) + "\n")
    print("  -> data/social/mortality.csv")
    print("Done.")


if __name__ == "__main__":
    main()
