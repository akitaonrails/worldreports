#!/usr/bin/env python3
"""Refresh the ISTAT series for Italy into sidecar CSVs.

Usage:  python3 -I countries/italy/fetch/fetch_istat.py

ISTAT publishes its own statistics through the I.Stat SDMX web service
(esploradati.istat.it — the old sdmx.istat.it host 302s to a dead end).
No key is needed; `Accept: text/csv` turns the SDMX 2.1 GenericData
default into flat CSV. Flows used here:

  163_156                       quarterly GDP, levels, €mn (EDITION-stacked)
  167_747_DCSP_NIC2B2025_1      NIC consumer prices, annual means, one
                                segment per base (1995, 2010, 2015)
  167_745_DF_DCSP_NIC1B2025_1   NIC monthly, base 2025 (from January 2026)
  151_884                       RFL unemployment rate, quarterly SA
                                (EDITION-stacked)
  34_727                        absolute and relative poverty, new series
  22_289                        resident population at 1 January
  25_74                         live births
  26_29_DF_DCIS_DECESSI_2       deaths
  26_295                        life tables (life expectancy at birth)
  25_326_DF_DCIS_FECONDITA1_5   total fertility rate by mother's citizenship
  39_494_DF_DCIS_CMORTE1_RES_1  deaths by cause (European shortlist), by
                                territory of residence
  73_67                         crimes reported by the police to the
                                judiciary (Ministero dell'Interno SDI data)
  28_185_DF_DCIS_MIGRAZIONI_2/5 anagraphic migration from / to abroad
  29_7                          foreign residents at 1 January
  29_348_DF_DCIS_PERMSOGG1_1    stock of valid non-EU residence permits
  29_849                        acquisitions of citizenship

Things this service will do to you (all observed 2026-10-22):

**"NoRecordsFound" is HTTP 404** with a plain-text body: a 404 means the
KEY matched nothing, not that the flow is gone. A short key is HTTP 422
("Not enough key values in query, expecting N") — every dimension must be
named, a bare dot being the wildcard.

**EDITION stacks every vintage.** National accounts and labour flows
carry one copy of the whole history per release (eleven GDP editions in a
2006+ pull). Unpinned, each quarter repeats once per vintage. The fetcher
keeps only the latest edition, parsed as (year, month, release) from
codes like 2026M10 and 2026M9G11 — string order would put 2026M9 after
2026M10.

**Total codes differ per codelist.** TOTAL, ALL, WORLD, 99, 9 and the
geographic aggregate X1033 ("world") all mean "everything" somewhere.
MARITAL_STATUS=99 is the births total; COUNTRY_BIRTH has no TOTAL at all
and X1033 is the deaths total; immigration is filed under REF_AREA=ITTOT
while emigration, in the twin subflow, is under REF_AREA=IT.

**Unkeyed flows are heavy** (births 22MB for two years; causes of death
~29MB for one) and the server throttles after repeated large pulls. Every
query here is keyed to the national cells, requests are spaced, and each
response is cached in cache/ — delete a cache file to refresh it.

Outputs are `*_from_istat.csv` sidecars under data/. Nothing here
overwrites a curated file. A flow that will not answer is reported as
PENDING and its sidecar is not written; a must-verify value that does not
match fails the run.
"""
from __future__ import annotations

import csv
import io
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache"

BASE = "https://esploradati.istat.it/SDMXWS/rest"
Y0, Y1 = 2006, 2026
SPACING = 3.0          # seconds between live requests (server throttles)

_last_request = 0.0
_host_down = False
PENDING: list[str] = []


class NoRecords(Exception):
    """HTTP 404 NoRecordsFound: the key matched nothing."""


# ---- minimal I.Stat SDMX client (cached in cache/) ---------------------

def _http(url: str, accept: str) -> bytes:
    global _last_request
    wait = SPACING - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers={"Accept": accept})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.read()
    finally:
        _last_request = time.monotonic()


def _fetch_cached(cache_file: Path, url: str, accept: str,
                  check) -> bytes:
    CACHE.mkdir(exist_ok=True)
    global _host_down
    if cache_file.exists():
        return cache_file.read_bytes()
    if _host_down:
        raise RuntimeError(f"host unreachable earlier in this run: {url}")
    last: Exception | None = None
    for attempt in range(3):
        try:
            raw = _http(url, accept)
            check(raw)
            cache_file.write_bytes(raw)
            return raw
        except urllib.error.HTTPError as e:
            body = e.read()[:200].decode("utf-8", "replace")
            if e.code == 404 and "NoRecordsFound" in body:
                raise NoRecords(url) from None
            if e.code in (400, 422):          # a bad key never heals
                raise RuntimeError(f"HTTP {e.code} {body!r}: {url}") from None
            last = e
        except Exception as e:  # noqa: BLE001
            last = e
        time.sleep(10 * (attempt + 1))
    if isinstance(last, (urllib.error.URLError, TimeoutError)) and not \
            isinstance(last, urllib.error.HTTPError):
        # Connection-level failure three times running: the server is
        # throttling or down. Stop hammering it; the rest go PENDING.
        _host_down = True
    raise RuntimeError(f"istat {url}: {last}")


def data(flow: str, key: str, query: str = f"startPeriod={Y0}") -> list[dict]:
    """One keyed SDMX query as a list of CSV rows (dicts).

    `query` is the raw query string (startPeriod, detail); the cache file
    is named after flow + key + query, so a changed query is a new pull.
    """
    url = f"{BASE}/data/{flow}/{key}" + (f"?{query}" if query else "")
    safe = re.sub(r"[^A-Za-z0-9_.+-]", "_", f"{flow}__{key}__{query}")
    cache_file = CACHE / f"istat_{safe}.csv"

    def check(raw: bytes) -> None:
        if not raw.startswith(b"DATAFLOW,"):
            raise ValueError(f"not SDMX-CSV: {raw[:80]!r}")

    raw = _fetch_cached(cache_file, url, "text/csv", check)
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    if not rows:
        raise NoRecords(url)
    return rows


def codelist(cl_id: str, lang: str = "en") -> dict[str, str]:
    """{code: name} for one ISTAT codelist (SDMX-ML structure message)."""
    url = f"{BASE}/codelist/IT1/{cl_id}/1.0"
    cache_file = CACHE / f"istat_codelist_{cl_id}.xml"

    def check(raw: bytes) -> None:
        if b"<structure:Codelist" not in raw:
            raise ValueError("not a codelist message")

    text = _fetch_cached(cache_file, url, "application/xml",
                         check).decode("utf-8")
    out = {}
    for cid, body in re.findall(
            r'<structure:Code id="([^"]+)"[^>]*>(.*?)</structure:Code>',
            text, re.S):
        m = re.search(rf'<common:Name xml:lang="{lang}">([^<]*)', body)
        if m:
            out[cid] = m.group(1).strip()
    return out


# ---- row helpers -------------------------------------------------------

def edition_key(code: str) -> tuple[int, int, int]:
    m = re.fullmatch(r"(\d{4})M(\d{1,2})(?:G(\d+))?", code)
    if not m:
        raise ValueError(f"unparsed EDITION code {code!r}")
    return int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)


def latest_edition(rows: list[dict]) -> tuple[str, list[dict]]:
    """Keep only the newest vintage — the EDITION trap."""
    editions = {r["EDITION"] for r in rows}
    latest = max(editions, key=edition_key)
    return latest, [r for r in rows if r["EDITION"] == latest]


def select(rows: list[dict], **dims: str) -> list[dict]:
    return [r for r in rows if all(r.get(k) == v for k, v in dims.items())]


def annual(rows: list[dict], **dims: str) -> dict[int, float]:
    """{year: value} for one series; two values for one year is an error."""
    out: dict[int, float] = {}
    for r in select(rows, **dims):
        if r["OBS_VALUE"] in ("", "NaN"):
            continue
        y = int(r["TIME_PERIOD"][:4])
        if y in out:
            raise AssertionError(f"two values for {y} in {dims}")
        out[y] = float(r["OBS_VALUE"])
    return out


def quarterly(rows: list[dict]) -> dict[int, dict[int, float]]:
    """{year: {quarter: value}} from TIME_PERIOD codes like 2025-Q3."""
    out: dict[int, dict[int, float]] = {}
    for r in rows:
        if r["OBS_VALUE"] in ("", "NaN"):
            continue
        y, q = r["TIME_PERIOD"].split("-Q")
        slot = out.setdefault(int(y), {})
        if int(q) in slot:
            raise AssertionError(f"quarter {r['TIME_PERIOD']} repeats")
        slot[int(q)] = float(r["OBS_VALUE"])
    return out


def statuses(rows: list[dict], **dims: str) -> dict[int, str]:
    return {int(r["TIME_PERIOD"][:4]): r.get("OBS_STATUS", "")
            for r in select(rows, **dims) if r.get("OBS_STATUS")}


def fmt(v, spec: str) -> str:
    return "" if v is None else format(v, spec)


def write(rel: str, comments: list[str], header: list[str],
          rows: list[list[str]]) -> None:
    path = DATA / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    # A column with no value at all is a flow that did not answer this run
    # (see the PENDING log): it is left out rather than shipped as blanks.
    empty = [i for i in range(1, len(header))
             if not any(r[i] for r in rows)]
    if empty:
        comments = comments + [
            "PENDING at fetch: column(s) " + ", ".join(header[i] for i in empty)
            + " omitted — the flow did not answer; rerun fetch_istat.py."]
        keep = [i for i in range(len(header)) if i not in empty]
        header = [header[i] for i in keep]
        rows = [[r[i] for i in keep] for r in rows]
    lines = [f"# {c}" for c in comments] + [",".join(header)]
    lines += [",".join(r) for r in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  -> data/{rel}  {len(rows)} rows")


def by_year(header: list[str], cols: list[dict], specs: list[str],
            years=range(Y0, Y1 + 1)) -> tuple[list[str], list[list[str]]]:
    out = []
    for y in years:
        out.append([str(y)] + [fmt(c.get(y), s) for c, s in zip(cols, specs)])
    return header, out


def guarded(name: str, fn) -> None:
    """Run one optional block; a dead flow becomes PENDING, not a crash.

    AssertionError is NOT caught — a must-verify mismatch fails the run.
    """
    try:
        fn()
    except AssertionError:
        raise
    except Exception as e:  # noqa: BLE001
        msg = f"{name}: {type(e).__name__}: {e}"
        PENDING.append(msg)
        print(f"  !! PENDING {msg}", file=sys.stderr)


# ---- the series --------------------------------------------------------

def gdp() -> None:
    rows = data("163_156", "Q.IT.B1GQ_B_W2_S1.V.N.")
    edition, rows = latest_edition(rows)
    q = quarterly(rows)
    # Must-verify: 2025's raw quarters sum to €2,265,002.6mn (Eurostat
    # nama_10_gdp reads 2,265,002.5 — the same transmission).
    s25 = round(sum(q[2025].values()), 1)
    assert len(q[2025]) == 4 and s25 == 2265002.6, f"GDP 2025 sums {s25}"
    print(f"  ok GDP 2025 = {s25:,.1f} €mn (edition {edition})")
    tot = {y: sum(v.values()) for y, v in q.items() if len(v) == 4}
    nq = {y: len(v) for y, v in q.items()}
    write("macro/gdp_from_istat.csv",
          [f"ISTAT 163_156, GDP at current prices, raw (unadjusted) quarterly levels, EDITION pinned to {edition} (latest vintage).",
           "Annual figure = SUM of the four raw quarters; a year with fewer than four published quarters is blank, its count in `quarters`."],
          *by_year(["year", "gdp_eurmn", "quarters"], [tot, nq],
                   [".1f", "d"]))


def nic() -> None:
    # The base-2015 general index is the must-verify cut (the manifest URL).
    b15 = annual(data("167_747_DCSP_NIC2B2025_1", "A.IT.40.4.00"))
    assert b15.get(2024) == 120.8 and b15.get(2025) == 122.6, \
        f"NIC base 2015: 2024={b15.get(2024)} 2025={b15.get(2025)}"
    print("  ok NIC base 2015: 2024 = 120.8, 2025 = 122.6")
    # DATA_TYPE carries one segment per base: 2 = base 1995 (to 2010),
    # 10 = base 2010 (2011-2015), 40 = base 2015 (2016-2025); MEASURE 8 is
    # ISTAT's published annual-average rate.
    idx: dict[str, dict[int, float]] = {"1995": {}, "2010": {}, "2015": b15}
    rate: dict[int, float] = {}
    try:
        rows = data("167_747_DCSP_NIC2B2025_1", "A.IT.2+10+40.4+8.00",
                    query="")
        for base, dt in (("1995", "2"), ("2010", "10")):
            idx[base] = annual(rows, DATA_TYPE=dt, MEASURE="4")
        assert annual(rows, DATA_TYPE="40", MEASURE="4") == b15, \
            "base-2015 index differs between the two pulls"
        for dt in ("2", "10", "40"):
            for y, v in annual(rows, DATA_TYPE=dt, MEASURE="8").items():
                assert y not in rate, f"NIC rate {y} published on two bases"
                rate[y] = v
        assert rate.get(2025) == 1.5, f"NIC 2025 rate {rate.get(2025)}"
        print("  ok NIC earlier bases staged; 2025 rate = +1.5%")
    except (RuntimeError, NoRecords, OSError) as e:
        PENDING.append(f"NIC bases 1995/2010 + published rates: {e}")
        print(f"  !! PENDING NIC earlier bases: {e}", file=sys.stderr)

    # The base-2025 series starts January 2026 in its own flow.
    months: dict[int, list[float]] = {}
    try:
        m26 = select(data("167_745_DF_DCSP_NIC1B2025_1", "M.IT.85..00",
                          query=""), MEASURE="4")
        for r in m26:
            months.setdefault(int(r["TIME_PERIOD"][:4]), []).append(
                float(r["OBS_VALUE"]))
    except (RuntimeError, NoRecords, OSError) as e:
        PENDING.append(f"NIC base 2025 monthly (167_745): {e}")
        print(f"  !! PENDING NIC base 2025: {e}", file=sys.stderr)
    b25 = {y: sum(v) / len(v) for y, v in months.items()}
    nmon = {y: 12 for b in idx.values() for y in b}
    nmon.update({y: len(v) for y, v in months.items()})
    write("macro/nic_from_istat.csv",
          ["ISTAT NIC (consumer prices for the whole nation), general index, annual mean. NOT the HICP.",
           "FOUR BASES, NEVER SPLICED: each index column is the series ISTAT published on that base (167_747 DATA_TYPE 2/10/40; base-2025 from 167_745, monthly, starting 2026-01).",
           "THE 2025 REBASE SEAM: with the January 2026 release ISTAT moved the NIC to base 2025=100 (flow 167_745); 1996-2025 stay on base 2015 in flow 167_747. Same base change, same year as Spain's IPC.",
           "rate_avg is ISTAT's own published annual-average rate of change (MEASURE 8), which ISTAT carries across its base changes.",
           "2026 is the running year: index_b2025 is the mean of the months published so far (count in `months`), not an annual mean."],
          *by_year(["year", "index_b1995", "index_b2010", "index_b2015",
                    "index_b2025", "rate_avg", "months"],
                   [idx["1995"], idx["2010"], b15, b25, rate, nmon],
                   [".1f", ".1f", ".1f", ".2f", ".1f", "d"]))


def unemployment() -> None:
    rows = data("151_884", "Q.IT.UNEM_R.9.Y15-74.")
    edition, rows = latest_edition(rows)
    q = quarterly(rows)
    q24 = [round(q[2024][i], 2) for i in (1, 2, 3, 4)]
    assert q24 == [7.10, 6.66, 6.30, 6.23], f"RFL 2024 quarters {q24}"
    mean24 = round(sum(q[2024].values()) / 4, 1)
    assert mean24 == 6.6, f"RFL 2024 mean {mean24}"
    first = min(q)
    print(f"  ok RFL 2024 quarters {q24}, mean {mean24} (edition {edition});"
          f" current-regulation series starts {first}-Q{min(q[first])}")
    avg = {y: sum(v.values()) / 4 for y, v in q.items() if len(v) == 4}
    nq = {y: len(v) for y, v in q.items()}
    write("macro/unemployment_from_istat.csv",
          [f"ISTAT RFL (labour force survey), unemployment rate 15-74, quarterly seasonally adjusted, flow 151_884, EDITION pinned to {edition}.",
           "Annual figure = MEAN of the four SA quarters; a year with fewer quarters is blank, its count in `quarters`.",
           f"The current-regulation flow is BACKCAST: its latest edition starts {first}-Q{min(q[first])}, so 2006-2020 here are on the post-2021 (EU 2019/1700) definitions — one series, no old-regulation splice needed.",
           "Eurostat une_rt_a (unemployment_from_estat.csv) starts only in 2009 for Italy; this file covers 2006-2008."],
          *by_year(["year", "unemp_rate_avg", "quarters"], [avg, nq],
                   [".2f", "d"]))


def poverty() -> None:
    rows = data("34_727", "A.2..ALL.TOT.HH.TOTAL.99.ALL.9.TOTAL",
                query="detail=dataonly")
    hh = annual(rows, DATA_TYPE="INCID_POVASS_FAM")
    rel = annual(rows, DATA_TYPE="INCID_POVREL_FAM")
    assert max(hh) >= 2025, f"34_727 ends {max(hh)} — not the current series"
    # Pinned at fetch 2026-10-22 (regression pin, read from the payload).
    assert hh[2025] == 8.1 and hh[2014] == 6.0, \
        f"34_727 absolute poverty hh 2014={hh.get(2014)} 2025={hh.get(2025)}"
    print(f"  ok poverty 34_727 covers {min(hh)}-{max(hh)}; "
          f"absolute hh 2025 = {hh[2025]}")
    write("social/poverty_abs_from_istat.csv",
          ["ISTAT 34_727 'Povertà nuove serie' — household incidence (%), national (REF_AREA code '2' is Italy in this codelist).",
           "abs_hh = ABSOLUTE poverty (fixed basket); rel_hh = RELATIVE poverty (national line). The new series starts 2014 on the revised basket.",
           "Flow 34_201 is the old, interrupted series (ends 2013): a definitional break — two columns if ever drawn, never spliced.",
           "Individual incidence (INCID_POVASS_INDIV) uses different cross-dimension totals and is not staged here."],
          *by_year(["year", "abs_hh", "rel_hh"], [hh, rel], [".1f", ".1f"]))


def population() -> None:
    rows = data("22_289", "A.IT.JAN.9.TOTAL.99")
    pop = annual(rows)
    st = statuses(rows)
    assert pop.get(2025) == 58943464, f"pop 1-Jan-2025 {pop.get(2025)}"
    print(f"  ok population 1-Jan-2025 = {pop[2025]:,.0f} "
          f"(22_289 covers {min(pop)}-{max(pop)})")
    write("social/population_from_istat.csv",
          [f"ISTAT 22_289, resident population at 1 January, national. This flow carries the PERMANENT-CENSUS series only ({min(pop)} onward).",
           "Years before are blank, not missing data: the post-2011-census and intercensal reconstructions live in other flows (164_*) on a different basis — never splice them on.",
           "`status` is ISTAT's OBS_STATUS (e = estimate)."],
          *by_year(["year", "population", "status"],
                   [pop, st], [".0f", "s"]))


def vital() -> None:
    b = data("25_74",
             "A.IT.LBIRTH.TOTAL.TOTAL.TOTAL.ALL.99.99.ALL.ALL.WORLD.ALL")
    births = annual(b)
    assert births.get(2024) == 369944, f"births 2024 {births.get(2024)}"
    d = data("26_29_DF_DCIS_DECESSI_2", "A.IT.DEATH.9.TOTAL.99.TOTAL..99",
             query="")
    d = select(d, COUNTRY_BIRTH="X1033")
    deaths = annual(d)
    # Cross-check with Eurostat demo_gind DEATH 2024 (verified 2026-10-22).
    assert deaths.get(2024) == 653109, f"deaths 2024 {deaths.get(2024)}"
    print(f"  ok births 2024 = {births[2024]:,.0f}; deaths 2024 = "
          f"{deaths[2024]:,.0f} (deaths flow starts {min(deaths)})")
    write("social/vital_from_istat.csv",
          ["ISTAT live births (25_74; MARITAL_STATUS 99/99 and CITIZEN_FOREIN_OFBIRTH=WORLD are the totals) and deaths (26_29_DF_DCIS_DECESSI_2; COUNTRY_BIRTH=X1033 'world' is the total — the codelist has no TOTAL).",
           f"Deaths flow covers {min(deaths)}-{max(deaths)} only; earlier years are blank (Eurostat demo_gind is the 2006+ cross-check). The latest births year is provisional."],
          *by_year(["year", "births", "deaths"], [births, deaths],
                   [".0f", ".0f"]))


def lifexp() -> None:
    rows = data("26_295", "A.IT.LIFEXP..Y0")
    m, f, t = (annual(rows, SEX=s) for s in ("1", "2", "9"))
    print(f"  life expectancy at birth {max(t)}: {t[max(t)]}")
    write("social/lifexp_from_istat.csv",
          ["ISTAT 26_295 life tables: life expectancy at birth (DATA_TYPE=LIFEXP, AGE=Y0), years, by sex."],
          *by_year(["year", "lifexp_male", "lifexp_female", "lifexp_total"],
                   [m, f, t], [".2f", ".2f", ".2f"]))


def fertility() -> None:
    rows = data("25_326_DF_DCIS_FECONDITA1_5", "A.IT.TOTFERR..TOTAL")
    tot, ita, frg = (annual(rows, CITIZENSHIP=c)
                     for c in ("TOTAL", "ITL", "FRG"))
    # Eurostat demo_find TFR 2024 = 1.18 (verified 2026-10-22).
    assert round(tot.get(2024, 0), 2) == 1.18, f"TFR 2024 {tot.get(2024)}"
    print(f"  ok TFR 2024 = {tot[2024]} (Italian {ita.get(2024)}, "
          f"foreign {frg.get(2024)})")
    write("social/fertility_from_istat.csv",
          ["ISTAT 25_326 total fertility rate, by citizenship of the mother (TOTAL / ITL Italian / FRG foreign)."],
          *by_year(["year", "tfr_total", "tfr_italian", "tfr_foreign"],
                   [tot, ita, frg], [".2f", ".2f", ".2f"]))


CAUSES_KEY = "A.IT.DEATH.TOTAL.9.99.99.YEAR.ALL.TOTAL.ALL.WORLD."
ASSAULT = "17_3"            # "homicide, assault" (ICD-10 X85-Y09)


def causes_of_death() -> dict[int, float]:
    rows = data("39_494_DF_DCIS_CMORTE1_RES_1", CAUSES_KEY)
    names = codelist("CL_CAUSEMORTE_SL")
    series: dict[str, dict[int, float]] = {}
    for code in sorted({r["UNDERLY_DEATH_EUSL"] for r in rows}):
        series[code] = annual(rows, UNDERLY_DEATH_EUSL=code)
    unnamed = [c for c in series if c not in names]
    assert not unnamed, f"cause codes missing from codelist: {unnamed}"
    used = [names[c] for c in series]
    assert len(set(used)) == len(used), "two shortlist codes share a name"
    assert names[ASSAULT] == "homicide, assault", names.get(ASSAULT)
    assert names["99"] == "all causes of death", names.get("99")
    homicide = series[ASSAULT]
    # Pinned at fetch 2026-10-22 (regression pin, read from the payload).
    assert homicide.get(2023) == 239 and series["99"].get(2023) == 662652, \
        f"assault 2023 {homicide.get(2023)}, all {series['99'].get(2023)}"
    last = max(series["99"])
    print(f"  ok causes of death: {len(series)} shortlist codes, "
          f"{min(series['99'])}-{last}; assault {last} = {homicide[last]:.0f}")
    out = []
    for y in range(Y0, Y1 + 1):
        for code in sorted(series):
            v = series[code].get(y)
            if v is not None:
                out.append([str(y), code, '"' + names[code].replace('"', "'")
                            + '"', f"{v:.0f}"])
    write("social/causes_of_death_from_istat.csv",
          ["ISTAT 39_494 deaths by underlying cause, European shortlist (CL_CAUSEMORTE_SL), territory of RESIDENCE, national, both sexes, all ages.",
           "The 39_493 twin counts by territory of EVENT — a different count, never mixed with this one.",
           "Codes nest (2 > 2_1 > 2_1_1 ...; 'of which' rows are subsets): never sum the column. 99 = all causes; 20* (Covid-19) exist from 2020.",
           "All-causes here (certificates, residents) is not the deaths figure in vital_from_istat.csv (population register) — two counts."],
          ["year", "code", "cause", "deaths"], out)
    return homicide


def homicide_police() -> dict[int, float]:
    # Intentional homicide, every DATA_TYPE / offender / period cut (small).
    rows = select(data("73_67", "A.IT..INTENHOM.."),
                  Y_KNOWN_OFFENDER_IDEN="9", REFERENCE_PERIOD_CRIME="YRDUR")
    n = {"INTENHOM": annual(rows, DATA_TYPE="CRIMEN")}
    rate = annual(rows, DATA_TYPE="CRIMET")
    try:
        sub = data("73_67", "A.IT.CRIMEN.ATTEMPHOM+MAFIAHOM+INFANTHOM.9.YRDUR")
        for t in ("ATTEMPHOM", "MAFIAHOM", "INFANTHOM"):
            n[t] = annual(sub, TYPE_CRIME=t)
    except (RuntimeError, NoRecords, OSError) as e:
        PENDING.append(f"73_67 attempted/mafia/infant homicide columns: {e}")
        print(f"  !! PENDING homicide subsets: {e}", file=sys.stderr)
    for t in ("ATTEMPHOM", "MAFIAHOM", "INFANTHOM"):
        n.setdefault(t, {})
    assert rate.get(2024) == 0.6, f"INTENHOM rate 2024 {rate.get(2024)}"
    print(f"  ok police intentional homicide 2024 = {rate[2024]}/100k "
          f"({n['INTENHOM'][2024]:.0f} offences)")
    write("security/homicide_police_from_istat.csv",
          ["ISTAT 73_67, crimes reported by the police forces to the judiciary — Ministero dell'Interno SDI data via ISTAT. National, all offender statuses (Y_KNOWN_OFFENDER_IDEN=9), offences recorded in the year (REFERENCE_PERIOD_CRIME=YRDUR).",
           "intenhom = completed intentional homicides (omicidi volontari consumati); per100k is ISTAT's own rate (CRIMET), published to one decimal.",
           "mafiahom and infanthom are SUBSETS of intenhom (draw as subsets, never stacked as peers); attemphom (attempted) is a separate offence.",
           "Counted at the place of the offence by the police; the death-certificate count is homicide_vital_from_istat.csv."],
          *by_year(["year", "intenhom", "intenhom_per100k", "attemphom",
                    "mafiahom", "infanthom"],
                   [n["INTENHOM"], rate, n["ATTEMPHOM"], n["MAFIAHOM"],
                    n["INFANTHOM"]],
                   [".0f", ".1f", ".0f", ".0f", ".0f"]))
    return n["INTENHOM"]


def homicide_vital(vital_h: dict[int, float],
                   police: dict[int, float] | None) -> None:
    both = sorted(y for y in vital_h if police and y in police)
    if both:
        y = both[-1]
        print(f"  two counts {y}: certificates {vital_h[y]:.0f} vs police "
              f"{police[y]:.0f} ({vital_h[y] / police[y] - 1:+.0%})")
    write("security/homicide_vital_from_istat.csv",
          ["ISTAT 39_494, deaths whose underlying cause is assault (European shortlist 17_3, ICD-10 X85-Y09), national, by RESIDENCE of the victim.",
           "The death-certificate count of homicide; the police count is homicide_police_from_istat.csv. They disagree in both directions and neither is wrong (SOURCING §4): two columns, two lines, both labelled."],
          *by_year(["year", "assault_deaths"], [vital_h], [".0f"]))


def migration_flows() -> None:
    imm = data("28_185_DF_DCIS_MIGRAZIONI_2",
               "A.ITTOT.TREG.FREIGN.TOTAL+IT+FOR.9.TOTAL.ITTOT.X1033.X1033")
    emi = data("28_185_DF_DCIS_MIGRAZIONI_5",
               "A.IT.TDEREG.FREIGN.TOTAL+IT+FOR.9.TOTAL.ITTOT.X1033.X1033")
    i = {c: annual(imm, CITIZENSHIP=c) for c in ("TOTAL", "IT", "FOR")}
    e = {c: annual(emi, CITIZENSHIP=c) for c in ("TOTAL", "IT", "FOR")}
    for name, d in (("immigration", i), ("emigration", e)):
        for y in d["TOTAL"]:
            parts = d["IT"].get(y, 0) + d["FOR"].get(y, 0)
            assert parts == d["TOTAL"][y], f"{name} {y}: IT+FOR != TOTAL"
    bal = {y: i["TOTAL"][y] - e["TOTAL"][y]
           for y in i["TOTAL"] if y in e["TOTAL"]}
    last = max(bal)
    print(f"  ok migration {last}: in {i['TOTAL'][last]:,.0f}, out "
          f"{e['TOTAL'][last]:,.0f} (IT+FOR = TOTAL every year)")
    write("migration/migration_flows_from_istat.csv",
          ["ISTAT 28_185 anagraphic registrations (_2) and cancellations (_5) for change of residence from / to abroad, national, by citizenship (IT Italian, FOR foreign).",
           "Quirk: the immigration subflow files the national total under REF_AREA=ITTOT, the emigration subflow under REF_AREA=IT.",
           "The register-based national twin of Eurostat migr_imm1ctz / migr_emi1ctz; where the two diverge (e.g. 2008-2011) the vintage/definition difference is the story, not a splice."],
          *by_year(["year", "immigration", "immigration_italian",
                    "immigration_foreign", "emigration", "emigration_italian",
                    "emigration_foreign", "balance"],
                   [i["TOTAL"], i["IT"], i["FOR"], e["TOTAL"], e["IT"],
                    e["FOR"], bal], [".0f"] * 7))


def foreign_residents() -> None:
    rows = data("29_7", "A.IT...TOTAL", query="detail=dataonly")
    t, m, f = (annual(rows, SEX=s) for s in ("9", "1", "2"))
    assert t.get(2025) == 5371251, f"foreign residents 2025 {t.get(2025)}"
    print(f"  ok foreign residents 1-Jan-2025 = {t[2025]:,.0f} "
          f"(29_7 covers {min(t)}-{max(t)})")
    write("migration/foreign_residents_from_istat.csv",
          ["ISTAT 29_7, foreign-citizen residents at 1 January, national. Matches Eurostat migr_pop1ctz citizen=FOR_STLS.",
           f"This flow carries the permanent-census basis only ({min(t)} onward); earlier years are blank."],
          *by_year(["year", "foreign_residents", "male", "female"],
                   [t, m, f], [".0f"] * 3))


def permits_stock() -> None:
    rows = data("29_348_DF_DCIS_PERMSOGG1_1", "A.IT.RESPER.9.999.ALL..TOTAL.99",
                query="")
    tot, lt, nlt = (annual(rows, TYPE_RES_PERMIT=k)
                    for k in ("TOTAL", "LONGT", "NLONGT"))
    for y in tot:
        assert lt.get(y, 0) + nlt.get(y, 0) == tot[y], f"permits {y} parts"
    print(f"  ok permits stock {max(tot)} = {tot[max(tot)]:,.0f}")
    write("migration/permits_stock_from_istat.csv",
          ["ISTAT 29_348, STOCK of valid residence permits held by non-EU citizens at 1 January (MOSTREL_CCITENSHIP=999 = all non-EU citizenships).",
           "A permit is not a person and a stock is not a flow (SOURCING §4a): the pair to Eurostat first permits, never the same line.",
           "long_term = EU long-term residence permits (open-ended); non_long_term = time-limited permits."],
          *by_year(["year", "permits_total", "long_term", "non_long_term"],
                   [tot, lt, nlt], [".0f"] * 3))


def citizenship() -> None:
    rows = data("29_849", "A.IT.ACQCITIZ.9.WORLD..TOTAL", query="")
    cols = {k: annual(rows, ACQUISITION_PROCESS=k)
            for k in ("ALL", "MAT", "RS", "TRS")}
    print(f"  ok citizenship acquisitions {max(cols['ALL'])} = "
          f"{cols['ALL'][max(cols['ALL'])]:,.0f}")
    write("migration/citizenship_acquisitions_from_istat.csv",
          ["ISTAT 29_849, acquisitions of Italian citizenship by residents, national, by process: MAT marriage, RS residence, TRS transmission/election.",
           "The national twin of Eurostat migr_acq (naturalisation_from_estat.csv); the components need not sum to the total (other routes)."],
          *by_year(["year", "acquisitions", "by_marriage", "by_residence",
                    "by_transmission"],
                   [cols["ALL"], cols["MAT"], cols["RS"], cols["TRS"]],
                   [".0f"] * 4))


def main() -> None:
    print("Fetching ISTAT series for Italy...")
    # Must-verify series: a mismatch or a dead flow fails the run.
    gdp()
    nic()
    vital()
    foreign_residents()
    police = homicide_police()
    # The rest: a dead flow is PENDING, a wrong value still fails.
    guarded("unemployment 151_884", unemployment)
    guarded("poverty 34_727", poverty)
    guarded("population 22_289", population)
    guarded("life tables 26_295", lifexp)
    guarded("fertility 25_326", fertility)
    holder: dict = {}
    guarded("causes of death 39_494",
            lambda: holder.update(h=causes_of_death()))
    if "h" in holder:
        homicide_vital(holder["h"], police)
    guarded("migration flows 28_185", migration_flows)
    guarded("permits stock 29_348", permits_stock)
    guarded("citizenship 29_849", citizenship)
    if PENDING:
        print("PENDING (sidecar not written):", file=sys.stderr)
        for p in PENDING:
            print(f"  - {p}", file=sys.stderr)
    print("Done. Diff the *_from_istat.csv sidecars before adopting.")


if __name__ == "__main__":
    main()
