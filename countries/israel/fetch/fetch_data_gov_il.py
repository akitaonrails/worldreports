#!/usr/bin/env python3
"""Refresh the data.gov.il open-data series for Israel into sidecars.

Usage:  python3 -I countries/israel/fetch/fetch_data_gov_il.py

Three CKAN packages, all with datastore_active resources, verified live
2026-10-22:

  new-olim-by-years (Ministry of Aliyah and Integration): person-level
  PUF — one record per oleh (year_aliya, month_aliya, age, gender
  זכר/נקבה, erez_moza, ...). Aggregated here to year counts (and the
  male/female split as a completeness witness: male + female must equal
  the total). This is the LAW OF RETURN flow (1950/1952): olim are
  immigrants by a legal category with no foreign analogue, never an
  ordinary visa flow. Do not sum this with the PIBA permit counts
  below, or with asylum figures when they land — §4a says one line
  measures nothing in particular.

  stats_rish (Population and Immigration Authority, PIBA): monthly
  issuance rows with three count columns — חדשים new, הארכות
  extensions, תיקונים amendments. That split is migr_resfirst vs
  migr_resvalid made concrete: only חדשים behaves like a flow of
  first permits. The "מתעדכן" resource carries 2019 onward; the older
  per-month snapshots on the package are 2013-era tables with padded
  text and "קטן מ6" suppression cells, not numbers — they are refused
  by the int() check rather than parsed. Stocks (permits in force) are
  parked.

  crime_records_data (Israel Police): one dictionary resource of crime
  group/type codes plus one resource per year, 2021-2025, one row per
  recorded case (FictiveIDNumber) with its crime group and type.
  Homicide is inside the taxonomy: StatisticTypeKod 301 רצח (and 302,
  killing by hostile action, kept as its own column). 2006-2020 is not
  on the portal (meta.pending). Recorded-crime FILES, not victims, and
  place-of-occurrence geography; the CBS death-certificate count, when
  CBS returns, is the second series beside it (§4a).

Route notes, both "endpoints that lie" cases checked 2026-10-22:
  * datastore_search_sql answers 404 on this portal (GET and POST) —
    aggregation is done client-side over datastore_search pages, or by
    per-filter `total` reads where one number is wanted.
  * The raw file download URLs (aws-e / e .data.gov.il) are CloudFront-
    walled: 403 error HTML, so a presence test is worthless and the
    fetcher never tries them. Everything comes through the CKAN API.

Hebrew cell values stay UTF-8 in the sidecars (group names, visa class
names); the join keys are ASCII codes so any locale can label them
(DISCOVERY, RTL notes). An unmapped Hebrew value fails the run rather
than passing through as a mystery string.

Outputs:
  migration/olim_flow_from_datagovil.csv      year, olim, male, female, months
  migration/permits_from_datagovil.csv        year × visa class, new/ext/amend
  security/crime_by_group_from_datagovil.csv  year × crime group, cases
  security/homicide_police_from_datagovil.csv year, murder, hostile, person
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

NAME = "Israel"
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache" / "data_gov_il"
API = "https://data.gov.il/api/3/action/"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11, Linux x86_64)", "Accept": "application/json"}
PAGE = 32000   # the portal's proven page maximum

OLIM_PKG = "new-olim-by-years"
RISH_PKG = "stats_rish"
CRIME_PKG = "crime_records_data"
OLIM_YEARS = set(range(2015, 2026))
CRIME_YEARS = set(range(2021, 2026))
CRIME_TYPES = {301: "murder", 302: "hostile_activity"}
PERSON_GROUP = 300

MALE, FEMALE = "זכר", "נקבה"

# Visa class = first letter + number, e.g. א/2 -> A2. Full Hebrew
# alphabet mapped; anything unmapped fails the run loudly.
HE_LETTERS = {"א": "A", "ב": "B", "ג": "G", "ד": "D", "ה": "H", "ו": "V",
              "ז": "Z", "ח": "X", "ט": "T", "י": "Y", "כ": "K", "ך": "Kf",
              "ל": "L", "מ": "M", "ם": "Mf", "נ": "N", "ן": "Nf", "ס": "S",
              "ע": "E", "פ": "F", "ף": "Ff", "צ": "C", "ץ": "Cf", "ק": "K3",
              "ר": "R", "ש": "W", "ת": "S3"}

# Values read off the portal 2026-10-22. The olim ones are the PUF
# person counts the ministry itself published for 2022 (the
# Ukraine-arrival year); the BoI/Sochnut cross-check constant is
# hand-recorded beside it.
SPOT = [
    ("migration/olim_flow_from_datagovil.csv", "olim", 2022, 76601),
    ("migration/olim_flow_from_datagovil.csv", "olim", 2015, 31877),
    ("security/homicide_police_from_datagovil.csv", "murder_301", 2021, 156),
]
# (label, sidecar, column, year, hand constant, note, tolerance)
HAND_CROSS = [
    ("Aliyah 2022 (PUF count vs Sochnut year-end report, hand-entered)",
     "migration/olim_flow_from_datagovil.csv", "olim", 2022, 76800,
     "Jewish Agency/Sochnut 2022 aliyah ~76.8k", 0.02),
    ("Aliyah 2015 (ministry PUF vs CBS statistical release, hand-entered)",
     "migration/olim_flow_from_datagovil.csv", "olim", 2015, 31500,
     "CBS 2015 aliyah release ~31.5k (different counting agent: ministry "
     "registration file vs CBS's own tabulation)", 0.03),
]


class FetchError(RuntimeError):
    pass


# --------------------------------------------------------------- transport
def get_json(action: str, cache_name: str, check, **params) -> dict:
    """One CKAN API answer, shape-checked BEFORE caching."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / cache_name
    if path.exists():
        raw = path.read_bytes()
        try:
            p = json.loads(raw)
            if not p.get("success"):
                raise ValueError("cached CKAN answer is not success")
            check(p)
            return p
        except Exception as e:  # noqa: BLE001
            print(f"  stale cache {cache_name}: {e}", file=sys.stderr)
            path.unlink()
    url = API + action + "?" + urllib.parse.urlencode(params)
    last: Exception | None = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=180) as r:
                raw = r.read()
            p = json.loads(raw)          # a CloudFront error page would die here
            if not p.get("success"):
                raise ValueError(f"CKAN reports failure: {p.get('error')}")
            check(p)
            path.write_bytes(raw)
            return p
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"  {cache_name} attempt {attempt + 1}: {e}", file=sys.stderr)
            time.sleep(3 * (attempt + 1))
    raise FetchError(f"{url}: {last}")


def ds_total(resource_id: str, filters: dict | None = None) -> int:
    """`total` for a datastore query, without pulling the rows."""
    params = {"resource_id": resource_id, "limit": 0}
    if filters:
        params["filters"] = json.dumps(filters, ensure_ascii=False)
    tag = hashlib.md5(json.dumps(filters or {}, sort_keys=True).encode()).hexdigest()[:12]
    p = get_json("datastore_search",
                 f"total_{resource_id[:8]}_{tag}.json",
                 lambda p: p["result"]["total"], **params)
    return int(p["result"]["total"])


def ds_pages(resource_id: str, fields: str, cache_prefix: str) -> list[dict]:
    """Every row of a datastore resource, paged, fields trimmed.

    Pages are pulled in _id order and the collected count must match
    the announced total — a page that silently vanished fails the run.
    """
    first = get_json("datastore_search", f"{cache_prefix}_p0.json",
                     lambda p: p["result"]["records"],
                     resource_id=resource_id, limit=PAGE, offset=0,
                     sort="_id", fields=fields)
    total = int(first["result"]["total"])
    rows = list(first["result"]["records"])
    while len(rows) < total:
        p = get_json("datastore_search",
                     f"{cache_prefix}_p{len(rows) // PAGE}.json",
                     lambda p: p["result"]["records"],
                     resource_id=resource_id, limit=PAGE,
                     offset=len(rows), sort="_id", fields=fields)
        page = p["result"]["records"]
        if not page:
            raise FetchError(f"{resource_id}: page empty at offset {len(rows)} "
                             f"of total {total}")
        rows += page
    if len(rows) != total:
        raise FetchError(f"{resource_id}: collected {len(rows)} != total {total}")
    return rows


def resources(pkg: str, want_datastore: bool = True) -> list[dict]:
    def check(p: dict) -> None:
        assert p["result"]["resources"], "package has no resources"
    p = get_json("package_show", f"pkg_{pkg}.json", check, id=pkg)
    res = [r for r in p["result"]["resources"]
           if r.get("datastore_active") or not want_datastore]
    return res


def year_resource(res: list[dict], year: int) -> str:
    hits = [r["id"] for r in res
            if re.search(str(year), r.get("name") or "")
            and (r.get("format") or "").upper() == "CSV"]
    if len(hits) != 1:
        raise FetchError(f"expected exactly one datastore CSV naming {year}, "
                         f"got {len(hits)}")
    return hits[0]


def visa_code(cls: str) -> str:
    """א/2 -> A2; statutory-text classes like "ס' 2)א(5" get every
    non-alnum Hebrew/punctuation run folded to one underscore. Any
    unmapped character that is neither Hebrew letter, digit, punctuation
    nor space fails the run; code collisions are caught in pull_permits
    (two classes must not share one code)."""
    cls = cls.strip()
    if not cls:
        return "none"
    out: list[str] = []
    for ch in cls:
        if ch in HE_LETTERS:
            out.append(HE_LETTERS[ch])
        elif ch.isdigit():
            out.append(ch)
        elif ch == "/" or ch == " " or ch == "-":
            continue
        elif not ch.isascii() or ch in "'()\".,":
            out.append("_")          # statutory quoting: section markers
        else:
            raise FetchError(f"visa class {cls!r}: unmapped character {ch!r}")
    code = re.sub(r"_+", "_", "".join(out)).strip("_")
    if not code or not re.fullmatch(r"[A-Za-z0-9_]+", code):
        raise FetchError(f"visa class {cls!r}: code {code!r} not ascii-safe")
    return code


# --------------------------------------------------------------- olim
# The package changed schemas mid-run history: the 2015-2023 uploads use
# transliterated columns (year_aliya, month_aliya, gender) and the 2024
# upload (checked 2026-10-22) uses Hebrew ones (שנת עלייה, חודש עלייה,
# מגדר). A fields= request naming the wrong dialect 404s — an endpoint
# that lies by absence — so the schema is detected per resource from
# its own field list before any page is pulled.
OLIM_COLS = {
    "year": ("year_aliya", "שנת עלייה"),
    "month": ("month_aliya", "חודש עלייה"),
    "gender": ("gender", "מגדר"),
}


def ds_fields(resource_id: str, cache_name: str) -> list[str]:
    def check(p: dict) -> None:
        assert p["result"]["fields"], "no fields"
    p = get_json("datastore_search", cache_name, check,
                 resource_id=resource_id, limit=0)
    return [f["id"] for f in p["result"]["fields"]]


def pick_col(fields: list[str], candidates: tuple[str, ...], what: str,
             rid: str) -> str:
    for c in candidates:
        if c in fields:
            return c
    raise FetchError(f"{rid}: none of {candidates} for {what} in {fields}")


def pull_olim() -> list[str]:
    print("Ministry of Aliyah and Integration — new-olim-by-years (datastore)")
    res = resources(OLIM_PKG)
    per_year = defaultdict(Counter)
    months = defaultdict(set)
    for year in sorted(OLIM_YEARS):
        rid = year_resource(res, year)
        fields = ds_fields(rid, f"olim_{year}_fields.json")
        yc = pick_col(fields, OLIM_COLS["year"], "year of aliyah", rid)
        mc = pick_col(fields, OLIM_COLS["month"], "month of aliyah", rid)
        gc = pick_col(fields, OLIM_COLS["gender"], "gender", rid)
        rows = ds_pages(rid, f"{yc},{gc},{mc}", f"olim_{year}")
        for r in rows:
            y = int(r[yc])
            g = r[gc]
            if g == MALE:
                per_year[y]["male"] += 1
            elif g == FEMALE:
                per_year[y]["female"] += 1
            else:
                raise FetchError(f"unmapped gender {g!r} in {year} resource")
            months[y].add(int(r[mc]))
        n = sum(per_year[year].values())
        dialect = "hebrew" if yc.startswith("ש") else "translit"
        print(f"  {year}: {n:>6} olim ({dialect} schema, resource {rid[:8]})")
    table: dict[int, dict[str, float]] = {}
    for y in sorted(per_year):
        m, f = per_year[y]["male"], per_year[y]["female"]
        table[y] = {"olim": float(m + f), "olim_male": float(m),
                    "olim_female": float(f), "months": float(len(months[y]))}
    if table[2022]["olim"] < 60000:
        raise FetchError("2022 aliyah below 60k — the Ukraine-arrival year "
                         "cannot read smaller than that; wrong resource?")
    rel = "migration/olim_flow_from_datagovil.csv"
    _stage(rel, table, ["olim", "olim_male", "olim_female", "months"],
           {c: 0 for c in ("olim", "olim_male", "olim_female", "months")})
    print(f"  data/{rel}  {len(table)} rows (Law-of-Return flow; never "
          "summed with permits or asylum)")
    return [rel]


# --------------------------------------------------------------- permits
def pull_permits() -> str:
    print("PIBA — stats_rish (monthly issuance, מתעדכן resource)")
    res = [r for r in resources(RISH_PKG)
           if "מתעדכן" in (r.get("name") or "")
           and (r.get("format") or "").upper() == "CSV"]
    if len(res) != 1:
        raise FetchError(f"expected one live מתעדכן CSV resource, got {len(res)}")
    rid = res[0]["id"]
    rows = ds_pages(rid,
                    "שנת_רישום,חודש_רישום,אשרה,חדשים,הארכות,תיקונים",
                    "rish_live")
    agg: dict[int, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    months: dict[int, set] = defaultdict(set)
    for r in rows:
        y = int(r["שנת_רישום"])
        cls = (r["אשרה"] or "").strip()
        counts = agg[y][cls]
        for col, key in (("חדשים", "new"), ("הארכות", "ext"), ("תיקונים", "amend")):
            v = r.get(col)
            try:
                counts[key] += int(v)
            except (TypeError, ValueError):
                raise FetchError(f"rish {y} {cls!r}: non-numeric count "
                                 f"{v!r} — an old suppressed snapshot mixed "
                                 "into the live resource")
        months[y].add(int(r["חודש_רישום"]))
    rel = "migration/permits_from_datagovil.csv"
    table: dict[int, dict] = {}
    seen_code: dict[str, str] = {}
    path = DATA / rel
    header = "year,visa_class,visa_class_he,new_permits,extensions,amendments,months"
    lines = [header.split(",")]
    for y in sorted(agg):
        for cls in sorted(agg[y]):
            c = agg[y][cls]
            code = visa_code(cls)
            if seen_code.setdefault(code, cls) != cls:
                raise FetchError(f"visa class collision: {cls!r} and "
                                 f"{seen_code[code]!r} both map to {code!r}")
            lines.append([y, code, cls, c["new"], c["ext"], c["amend"],
                          len(months[y])])
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows(lines)
    text = buf.getvalue()
    if not any(row[3] > 0 for row in lines[1:]):
        raise FetchError("permit sidecar has no positive new-permit cell")
    if path.exists():
        first = next((ln for ln in path.read_text().splitlines()
                      if not ln.startswith("#")), "")
        if first != header:
            raise FetchError(f"refusing to overwrite {rel}: it holds {first!r}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    for y in sorted(agg):
        tot = sum(sum(c.values()) for c in agg[y].values())
        new = sum(c["new"] for c in agg[y].values())
        print(f"  {y}: {new:>6} new permits, {tot:>7} records "
              f"(only חדשים is a first-issuance flow — §4a)")
    print(f"  data/{rel}  {len(lines) - 1} rows")
    return rel


# --------------------------------------------------------------- crime
def pull_crime() -> list[str]:
    print("Israel Police — crime_records_data (dictionary + yearly files)")
    res = resources(CRIME_PKG)
    dict_rows = ds_pages(next(r["id"] for r in res
                              if "העבירות" in (r.get("name") or "")),
                         "StatisticCrimeGroupCode,StatisticCrimeGroupName",
                         "crime_dict")
    group_name: dict[int, str] = {}
    for r in dict_rows:
        code = int(r["StatisticCrimeGroupCode"])
        name = (r["StatisticCrimeGroupName"] or "").strip()
        if code in group_name and group_name[code] != name:
            raise FetchError(f"crime group {code}: two names "
                             f"{group_name[code]!r} / {name!r}")
        group_name[code] = name
    codes = sorted(group_name)
    print(f"  dictionary: {len(dict_rows)} rows, {len(codes)} group codes")

    rel_by_group = "security/crime_by_group_from_datagovil.csv"
    rel_homicide = "security/homicide_police_from_datagovil.csv"
    lines_g, lines_h = ["year,crime_group,group_he,cases"], ["year,murder_301,hostile_activity_302,person_offences_300"]
    for year in sorted(CRIME_YEARS):
        rid = year_resource(res, year)
        # One pass over the year's rows, columns trimmed: every count is
        # a local tally of the file itself, so it agrees with the file
        # total by construction. Per-filter `total` probes miss rows
        # whose group code is not in the dictionary (180 such rows in
        # 2021 — found by comparing the two methods the first run).
        rows = ds_pages(rid, "StatisticGroupKod,StatisticTypeKod,Quarter",
                        f"crime_{year}")
        if len(rows) != ds_total(rid):
            raise FetchError(f"{year}: paged rows != announced total")
        groups = Counter(int(r["StatisticGroupKod"]) if r["StatisticGroupKod"] is not None else -1 for r in rows)
        types = Counter(int(r["StatisticTypeKod"]) if r["StatisticTypeKod"] is not None else -1 for r in rows)
        quarters = {q for r in rows if (q := r["Quarter"])}
        unknown = sorted(set(groups) - set(group_name))
        if unknown:
            for c in unknown:
                print(f"  note {year}: {groups[c]} case rows carry group "
                      f"code {c}, absent from the dictionary — staged as {c} "
                      "with name 'לא מזוהה' rather than dropped")
        for c in sorted(groups):
            if groups[c]:
                name = group_name.get(c, "לא מזוהה")
                lines_g.append(f"{year},{c},\"{name}\",{groups[c]}")
        h = {code: types.get(code, 0) for code in CRIME_TYPES}
        person = groups.get(PERSON_GROUP, 0)
        lines_h.append(f"{year},{h[301]},{h[302]},{person}")
        print(f"  {year}: {len(rows):>7} case records, {len(quarters)} quarters, "
              f"murder(301) {h[301]}, hostile(302) {h[302]}, person(300) {person}")
    if len(quarters) < 4:
        print(f"  note: the newest year carries {len(quarters)} of 4 quarters — "
              "partial by construction, the plate labels it")
    for rel, lines, header in ((rel_by_group, lines_g, "year,crime_group,group_he,cases"),
                               (rel_homicide, lines_h, "year,murder_301,hostile_activity_302,person_offences_300")):
        path = DATA / rel
        if path.exists():
            first = next((ln for ln in path.read_text().splitlines()
                          if not ln.startswith("#")), "")
            if first != header:
                raise FetchError(f"refusing to overwrite {rel}: it holds {first!r}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n")
        print(f"  data/{rel}  {len(lines) - 1} rows")
    return [rel_by_group, rel_homicide]


# --------------------------------------------------------------- staging + checks
def _stage(rel: str, table: dict, columns: list[str], decimals: dict[str, int]) -> None:
    path = DATA / rel
    header = ",".join(["year", *columns])
    if path.exists():
        first = next((ln for ln in path.read_text().splitlines()
                      if not ln.startswith("#")), "")
        if first != header:
            raise FetchError(f"refusing to overwrite {rel}: it holds {first!r}")
    lines = [header]
    for y in sorted(table):
        cells = [f"{table[y][c]:.{decimals[c]}f}" for c in columns]
        lines.append(f"{y}," + ",".join(cells))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def read_stage(rel: str) -> list[dict]:
    with (DATA / rel).open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(ln for ln in fh if not ln.lstrip().startswith("#")))


def checks() -> None:
    bad = []
    for rel, column, year, want in SPOT:
        got = next((r.get(column) for r in read_stage(rel)
                    if r.get("year") == str(year)), None)
        if got is None or abs(float(got) - want) > max(abs(want) * 0.03, 1):
            bad.append(f"{rel} {column} {year}: want {want}, got {got}")
    for rel in ("migration/olim_flow_from_datagovil.csv",
                "security/crime_by_group_from_datagovil.csv",
                "security/homicide_police_from_datagovil.csv",
                "migration/permits_from_datagovil.csv"):
        rows = read_stage(rel)
        if not rows:
            bad.append(f"{rel}: empty")
    if bad:
        raise FetchError("spot checks failed:\n  " + "\n  ".join(bad))
    print(f"Spot checks: {len(SPOT)} values as expected")

    print("Cross-checks")
    for label, rel, column, year, want, note, tol in HAND_CROSS:
        got = float(next(r[column] for r in read_stage(rel)
                         if r["year"] == str(year)))
        diff = abs(got - want) / abs(want)
        if diff > tol:
            raise FetchError(f"{label}: {got} vs {note} {want} "
                             f"(rel {diff:.3f} > {tol})")
        print(f"  {label} {year}: {got:,.0f} | {note} {want:,.0f} — "
              f"ok (rel {diff:.4f} <= {tol})")
    # Homicide magnitude against the UNODC/WB rate the plate draws beside
    # it — different counting (police case files vs UNODC), so printed,
    # not asserted.
    try:
        sec = read_stage("security/security_from_wb.csv")
        pop = read_stage("demography/demography_from_wb.csv")
        hom = read_stage("security/homicide_police_from_datagovil.csv")
        for year in ("2021", "2022"):
            rate = next((float(r["homicide_per_100k"]) for r in sec
                         if r["year"] == year), None)
            p = next((float(r["population"]) for r in pop
                      if r["year"] == year), None)
            h = next(int(r["murder_301"]) for r in hom if r["year"] == year)
            if rate and p:
                print(f"  homicide {year}: police 301 = {h} "
                      f"({h / p * 1e5:.2f}/100k) | WB UNODC {rate}/100k — "
                      "printed only (two different counts, §4a)")
    except (FileNotFoundError, StopIteration):
        print("  (run fetch_harmonised.py to enable the homicide "
              "side-by-side print)")


def main() -> None:
    print(f"data.gov.il (CKAN datastore) for {NAME}")
    try:
        staged = [pull_olim(), pull_permits(), pull_crime()]
    except FetchError as e:
        print(f"!! {e}\nNothing written for the failed pull.", file=sys.stderr)
        sys.exit(1)
    try:
        checks()
    except FetchError as e:
        print(f"!! {e}", file=sys.stderr)
        sys.exit(1)
    flat = sorted({r for group in staged for r in ([group] if isinstance(group, str) else group)})
    print(f"Done ({len(flat)} sidecars). Diff before adopting.")


if __name__ == "__main__":
    main()
