#!/usr/bin/env python3
"""Refresh the Banca d'Italia series into sidecar CSVs.

Usage:  python3 -I countries/italy/fetch/fetch_bdi.py

Source: the Base Dati Statistica (BDS) inquiry app at
https://infostat.bancaditalia.it/inquiry/ — the legacy jQuery front end,
whose AJAX backend is a plain form-POST service, keyless:

  POST home?calltype=asin&service=GETINQUIRYSCOPE   session (cookie) + scope
  POST home?calltype=asin&service=PROSPETTODATI     one series' data table,
       CUBEIDS=<series code>, COMM=BANKITALIA, CTX=DIFF; 30 rows a page,
       further pages by re-posting the returned TABLEDATA as TABLEREQUEST
       with `rowsPageIndex` = a ROW offset (not a page number).

The 2023+ portal (statistiche.bancaditalia.it) is an Angular SPA over an
undocumented /api/ and is not used (SOURCES.yaml meta.pending).

Series (BDS codes, all verified live 2026-10-22):

  CFI_FA.Q.S1M.IT.F41.S1.W0.112.101.2   households+NPISH short-term loan
  CFI_FA.Q.S1M.IT.F42.S1.W0.112.101.2   liabilities, long-term likewise —
                                        financial accounts, quarterly
                                        STOCKS, € million
  SDDS_FS.Q.3700001.NPLL.902            gross non-performing loans / total
                                        loans, % (IMF FSI, SDDS Plus) —
                                        quarterly, published ratio
  BAM_BSIB.M.1070001.52000750.9.101.IT.SBI143.1000.997
                                        bad loans (sofferenze) on bank
                                        balance sheets, residents, monthly
                                        STOCK, € million — DISCONTINUED:
                                        last observation 2024-03
  BAM_BSIB.M.1070001.52000700.9.101.IT.S1P.1000.997
                                        bank loans to residents excl. MFIs
                                        and general government, monthly
                                        STOCK, € million
  BAM_MIR.M.1300010.MIR5411.9.950.1000.SBI17.EUR.110.212
                                        new-business rate, house purchase
  BAM_MIR.M.1300010.MIR5411.9.950.1000.SBI17.EUR.110.202
                                        new-business rate, consumer credit
  BAM_MIR.M.1300010.MIR5410.9.950.1000.SBI17.EUR.101.997
                                        outstanding-amounts rate, all
                                        household loans (all MIR: %, monthly)

Traps, all observed 2026-10-22:

**A bad call answers with an HTML "Risorsa Protetta" page under HTTP 500**
(and some answer the literal JSON `null` under HTTP 200). Every payload is
shape-checked — JSON, the expected keys, observations for the requested
cube — before it is cached, because a cached error page survives the
retry that would have fixed it.

**Pages come back NEWEST-FIRST, 30 rows each**, and the page size is fixed
server-side (asking for more is silently ignored). The fetcher walks the
row offset to `numTotRows`, de-duplicates on the date, sorts ascending,
and asserts the count matches the server's total.

**Stocks are read at their year-end observation** (December / Q4), never
summed; the running year carries its latest observation and the period
it belongs to, so the plate can label it as live.

**BdI publishes no disposable income** — that is ISTAT's national
accounts. The debt ratio's denominator is therefore Eurostat
nasa_10_nf_tr B6G S14_S15 (gross disposable income of households+NPISH,
current prices, € million — ISTAT's transmission), and the ratio column is
COMPUTED here and named so. The numerator stays Banca d'Italia's.

**The bad-loan stock stopped at 2024-03** (the BDS still lists it, LAST_UPD
2026, but the data end there). The headline NPL measure is therefore the
IMF-FSI gross NPL ratio, which uses the EBA/ITS non-performing definition
(from 2015); the sofferenze ÷ loans ratio is kept beside it as a computed,
narrower, older-definition column — never spliced into one line.

Outputs: data/credit/household_debt_from_bdi.csv,
         data/credit/npl_from_bdi.csv,
         data/credit/lending_rate_from_bdi.csv
"""
from __future__ import annotations

import http.cookiejar
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache"

BDS = "https://infostat.bancaditalia.it/inquiry/home?calltype=asin&service="
ESTAT = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/"
         "data/nasa_10_nf_tr?geo=IT&na_item=B6G&sector=S14_S15"
         "&unit=CP_MEUR&direct=RECV")
Y0, Y1 = 2006, 2026

SERIES = {
    "hh_loans_st": "CFI_FA.Q.S1M.IT.F41.S1.W0.112.101.2",
    "hh_loans_lt": "CFI_FA.Q.S1M.IT.F42.S1.W0.112.101.2",
    "npl_ratio_fsi": "SDDS_FS.Q.3700001.NPLL.902",
    "bad_loans": "BAM_BSIB.M.1070001.52000750.9.101.IT.SBI143.1000.997",
    "loans_total": "BAM_BSIB.M.1070001.52000700.9.101.IT.S1P.1000.997",
    "rate_house_new": "BAM_MIR.M.1300010.MIR5411.9.950.1000.SBI17.EUR.110.212",
    "rate_consumer_new":
        "BAM_MIR.M.1300010.MIR5411.9.950.1000.SBI17.EUR.110.202",
    "rate_hh_stock": "BAM_MIR.M.1300010.MIR5410.9.950.1000.SBI17.EUR.101.997",
}

# Keys of a PROSPETTODATI answer that are response-only and must not be
# echoed back inside the TABLEREQUEST of the next page.
_PAGE_FIELDS = ("columnsPageIndex", "columnsPerPage", "datawareHouseType",
                "isPieChart", "pureTimeSeries", "requestType")


class Session:
    """One BDS session: the cookie the scope call sets is what the data
    service keys its state on, so every call goes through one opener."""

    def __init__(self) -> None:
        jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(jar))
        scope = self.post("GETINQUIRYSCOPE", {})
        if not (isinstance(scope, dict)
                and scope.get("communityId") == "BANKITALIA"
                and scope.get("sessionId")):
            raise RuntimeError(f"bdi scope: unexpected payload {scope!r:.200}")

    def post(self, service: str, form: dict) -> object:
        body = urllib.parse.urlencode(form).encode()
        last = None
        for attempt in range(4):
            req = urllib.request.Request(BDS + service, data=body,
                                         method="POST")
            try:
                with self.opener.open(req, timeout=120) as r:
                    text = r.read().decode("utf-8")
            except urllib.error.HTTPError as e:
                # The "Risorsa Protetta" page: HTML under HTTP 500.
                last = f"HTTP {e.code}"
                time.sleep(2 * (attempt + 1))
                continue
            except OSError as e:
                last = e
                time.sleep(2 * (attempt + 1))
                continue
            if text.lstrip().startswith("<"):
                raise RuntimeError(f"bdi {service}: HTML instead of JSON")
            return json.loads(text)
        raise RuntimeError(f"bdi {service}: {last}")


def _form(code: str, table_request: dict | None = None) -> dict:
    # The row offset is honoured only when a PAGINATIONHANDLER rides along
    # (inside the TABLEREQUEST and as its own field); without it the server
    # silently returns page one again.
    ph = (table_request or {}).get("PAGINATIONHANDLER")
    return {
        "VIEW_MODE": "", "GRAPH_MODE": "", "COMM": "BANKITALIA",
        "CTX": "DIFF", "IDX": "1", "CUBESET": "", "INFOPATH": "",
        "CUBEIDS": code,
        "TABLEREQUEST": json.dumps(table_request) if table_request else "",
        "PAGINATIONHANDLER": json.dumps(ph) if ph else "",
        "keepTableRequest": "true" if table_request else "false",
        "isMultiMeasureSpecial": "false", "fromFiltra": "false",
        "fromMySpace": "false",
    }


def _observations(payload: object, code: str) -> list[dict]:
    """The page's observations, or an error if the shape is wrong."""
    if not isinstance(payload, dict) or "TABLEDATA" not in payload:
        raise RuntimeError(f"bdi {code}: no TABLEDATA in payload")
    obs = (payload["TABLEDATA"].get("result") or {}).get("observations")
    if not isinstance(obs, list) or not obs:
        raise RuntimeError(f"bdi {code}: empty observations")
    for o in obs:
        v = o.get("values", {})
        if not v.get("CUBEID", "").startswith(code):
            raise RuntimeError(f"bdi {code}: page carries {v.get('CUBEID')}")
    return obs


def download(sess: Session, code: str) -> dict:
    """Every observation of one series, walking the 30-row pages."""
    first = sess.post("PROSPETTODATI", _form(code))
    obs = _observations(first, code)
    total = first["PAGINATIONHANDLER"]["numTotRows"]
    tr = dict(first["TABLEDATA"])
    tr.pop("result", None)
    tr.pop("descriptions", None)
    for k in _PAGE_FIELDS:
        tr[k] = first[k]
    tr["rowsPerPage"] = first["rowsPerPage"]
    tr["PAGINATIONHANDLER"] = first["PAGINATIONHANDLER"]
    rows = {o["values"]["DATA_OSS"]: o["values"].get("VALORE") for o in obs}
    offset = len(obs)
    while offset < total:
        tr["rowsPageIndex"] = offset
        page = _observations(sess.post("PROSPETTODATI", _form(code, tr)),
                             code)
        before = len(rows)
        rows.update({o["values"]["DATA_OSS"]: o["values"].get("VALORE")
                     for o in page})
        if len(rows) == before:
            raise RuntimeError(f"bdi {code}: offset {offset} added nothing")
        offset += len(page)
    if len(rows) != total:
        raise RuntimeError(f"bdi {code}: {len(rows)} rows, server says {total}")
    name = (first.get("NODES") or [{}])[0].get("name", "")
    return {"code": code, "name": name, "numTotRows": total,
            "observations": sorted(rows.items())}


def fetch(name: str, sess_box: list) -> list[tuple[str, float]]:
    """[(yyyy-mm-dd, value)] ascending, from cache or the BDS."""
    CACHE.mkdir(exist_ok=True)
    code = SERIES[name]
    cache_file = CACHE / f"bdi_{name}.json"
    if cache_file.exists():
        blob = json.loads(cache_file.read_text())
    else:
        if not sess_box:
            sess_box.append(Session())
        blob = download(sess_box[0], code)
        cache_file.write_text(json.dumps(blob, ensure_ascii=False, indent=0))
    if blob.get("code") != code:
        raise RuntimeError(f"bdi cache {cache_file.name}: wrong code")
    out = []
    for d, v in blob["observations"]:
        if v in (None, "", "NaN", "null"):
            continue
        out.append((d[:10], float(v)))
    print(f"  {name}: {len(out)} obs {out[0][0]}..{out[-1][0]}  "
          f"({blob.get('name', '')[:70]})")
    return out


def fetch_gdi() -> dict[int, float]:
    """Households+NPISH gross disposable income, € million, by year."""
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / "estat_nasa_10_nf_tr_B6G_S14_S15.json"
    if cache_file.exists():
        d = json.loads(cache_file.read_text())
    else:
        last = None
        for attempt in range(4):
            try:
                with urllib.request.urlopen(ESTAT, timeout=120) as r:
                    d = json.loads(r.read().decode("utf-8"))
                if not d.get("value") or "time" not in d.get("dimension", {}):
                    raise ValueError("empty or malformed cube")
                cache_file.write_text(json.dumps(d))
                break
            except Exception as e:  # noqa: BLE001
                last = e
                time.sleep(2 * (attempt + 1))
        else:
            raise RuntimeError(f"estat nasa_10_nf_tr: {last}")
    if d["size"][:-1] != [1] * (len(d["size"]) - 1):
        raise RuntimeError("estat nasa_10_nf_tr: cube is not one series")
    idx = d["dimension"]["time"]["category"]["index"]
    return {int(t): float(d["value"][str(i)]) for t, i in idx.items()
            if str(i) in d["value"]}


def year_end(pairs: list[tuple[str, float]]) -> dict[int, tuple[str, float]]:
    """A stock's last observation of each year — December / Q4 when the
    year is complete, the latest reading for the running year."""
    out: dict[int, tuple[str, float]] = {}
    for d, v in pairs:
        out[int(d[:4])] = (d, v)
    return out


def annual_mean(pairs: list[tuple[str, float]], running: int
                ) -> dict[int, tuple[float, int]]:
    """(mean, months) for complete years, and for the running year with
    its month count beside it; an incomplete past year stays blank."""
    by_year: dict[int, list[float]] = {}
    for d, v in pairs:
        by_year.setdefault(int(d[:4]), []).append(v)
    return {y: (sum(vs) / len(vs), len(vs)) for y, vs in by_year.items()
            if len(vs) == 12 or y == running}


def write(rel: str, header: str, rows: list[list[str]]) -> None:
    path = DATA / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [header] + [",".join(r) for r in rows]
    path.write_text("\n".join(lines) + "\n")
    print(f"  -> data/{rel}  {len(rows)} rows")


def fmt(v: float | None, spec: str) -> str:
    return "" if v is None else format(v, spec)


def spot_checks(s: dict, gdi: dict[int, float]) -> None:
    """Live values read 2026-10-22, plus two magnitudes against Banca
    d'Italia's own published headlines. A revision that moves any of these
    must fail here and be looked at, not pass silently."""
    at = {k: dict(v) for k, v in s.items()}
    loans_2024 = at["hh_loans_st"]["2024-12-31"] + at["hh_loans_lt"]["2024-12-31"]
    assert loans_2024 == 798214.0, f"hh loans 2024-12 = {loans_2024}"
    assert gdi[2024] == 1426766.0, f"GDI 2024 = {gdi[2024]}"
    assert at["npl_ratio_fsi"]["2025-06-30"] == 2.6, \
        f"FSI NPL 2025-06 = {at['npl_ratio_fsi']['2025-06-30']}"
    assert at["bad_loans"]["2015-12-31"] == 200705.33
    assert at["loans_total"]["2026-08-31"] == 1511973.27
    assert at["rate_house_new"]["2025-12-31"] == 3.3844
    assert at["rate_consumer_new"]["2025-12-31"] == 8.3307
    assert at["rate_hh_stock"]["2025-12-31"] == 4.0316
    last_bad = s["bad_loans"][-1][0]
    assert last_bad == "2024-03-31", (
        f"bad-loan stock now ends {last_bad}: the series resumed or moved — "
        "revisit the NPL file's 2024+ rows")

    # Published headlines (read off the PDFs 2026-10-22):
    #  * Rapporto sulla stabilità finanziaria 1/2025, §1.3: household debt
    #    "ha raggiunto il valore minimo dal 2008, pari al 56,1 per cento"
    #    of disposable income (end-2024). Our computed ratio uses the
    #    financial-accounts loan stock (all lenders) over Eurostat's annual
    #    B6G, so a few tenths of difference is definitional; more is a bug.
    #  * RSF 2/2025 Appendix tav. A2, June 2025, all banks: gross NPL
    #    ratio 2,7 per cento. The IMF-FSI series has a narrower reporting
    #    perimeter (2.6); same order, one decimal apart.
    ratio_2024 = loans_2024 / gdi[2024] * 100
    assert abs(ratio_2024 - 56.1) < 0.5, f"debt/GDI 2024 = {ratio_2024:.1f}"
    assert abs(at["npl_ratio_fsi"]["2025-06-30"] - 2.7) <= 0.15
    print(f"  spot checks ok: debt/GDI 2024 = {ratio_2024:.1f} (BdI RSF 56.1); "
          f"gross NPL 2025-06 = 2.6 (BdI RSF A2 2.7)")


def main() -> None:
    print("Fetching Banca d'Italia series...")
    box: list = []
    s = {name: fetch(name, box) for name in SERIES}
    gdi = fetch_gdi()
    spot_checks(s, gdi)

    # ---- household debt ---------------------------------------------------
    # Loan STOCK at year-end (Q4); the running year carries its latest
    # quarter and no ratio (its income year is not closed).
    st, lt = year_end(s["hh_loans_st"]), year_end(s["hh_loans_lt"])
    rows = []
    for y in range(Y0, Y1 + 1):
        if y not in st or y not in lt:
            rows.append([str(y), "", "", fmt(gdi.get(y) and gdi[y] / 1000,
                                               ".1f"), ""])
            continue
        if st[y][0] != lt[y][0]:
            raise RuntimeError(f"hh loans {y}: periods {st[y][0]} {lt[y][0]}")
        period, loans = st[y][0], st[y][1] + lt[y][1]
        ratio = (loans / gdi[y] * 100
                 if y in gdi and period[5:7] == "12" else None)
        rows.append([str(y), period[:7], f"{loans / 1000:.1f}",
                     fmt(gdi.get(y) and gdi[y] / 1000, ".1f"),
                     fmt(ratio, ".1f")])
    write("credit/household_debt_from_bdi.csv",
          "year,loans_period,loans_eurbn,gdi_estat_eurbn,"
          "debt_pct_gdi_computed", rows)

    # ---- NPL ----------------------------------------------------------------
    # All three are STOCKS (or a ratio of stocks): the year is its last
    # observation, never a sum of months.
    fsi, bad, tot = (year_end(s[k]) for k in
                     ("npl_ratio_fsi", "bad_loans", "loans_total"))
    loans_at = dict(s["loans_total"])
    rows = []
    for y in range(Y0, Y1 + 1):
        f, b, t = fsi.get(y), bad.get(y), tot.get(y)
        # The computed ratio pairs both stocks at the SAME month (2024's
        # last bad-loan reading is March, so it divides by March loans).
        ratio = (b[1] / loans_at[b[0]] * 100
                 if b and b[0] in loans_at else None)
        rows.append([str(y),
                     f[0][:7] if f else "", fmt(f and f[1], ".1f"),
                     b[0][:7] if b else "", fmt(b and b[1], ".0f"),
                     fmt(ratio, ".2f"),
                     t[0][:7] if t else "", fmt(t and t[1], ".0f")])
    write("credit/npl_from_bdi.csv",
          "year,fsi_period,npl_gross_ratio_fsi,bad_loans_period,"
          "bad_loans_eur_mn,bad_loans_ratio_computed,loans_period,"
          "loans_eur_mn", rows)

    # ---- lending rates -----------------------------------------------------
    running = max(int(d[:4]) for d, _ in s["rate_house_new"])
    means = {k: annual_mean(s[k], running) for k in
             ("rate_house_new", "rate_consumer_new", "rate_hh_stock")}
    last_house = year_end(s["rate_house_new"])
    rows = []
    for y in range(Y0, Y1 + 1):
        h = means["rate_house_new"].get(y)
        c = means["rate_consumer_new"].get(y)
        o = means["rate_hh_stock"].get(y)
        e = last_house.get(y)
        rows.append([str(y), fmt(h and h[0], ".3f"), str(h[1]) if h else "0",
                     e[0][:7] if e else "", fmt(e and e[1], ".2f"),
                     fmt(c and c[0], ".3f"), fmt(o and o[0], ".3f")])
    write("credit/lending_rate_from_bdi.csv",
          "year,house_new_avg,months,house_new_last_period,house_new_last,"
          "consumer_new_avg,hh_outstanding_avg", rows)
    print("Done. Diff the sidecars before adopting.")


if __name__ == "__main__":
    main()
