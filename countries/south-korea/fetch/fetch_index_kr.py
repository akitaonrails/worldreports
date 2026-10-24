#!/usr/bin/env python3
"""Fetch official Korean indicators from e-나라지표 / 국가지표체계 (index.go.kr).

index.go.kr is the government's own indicator portal: every series on it is
published by the responsible ministry or by Statistics Korea, with the source
agency named on the page. It has no documented API, but the statistics-table
view is a plain server-rendered HTML table:

    /unity/potal/eNara/sub/showStblGams3.do
        ?stts_cd=<series>&idx_cd=<indicator>&freq=Y&period=<from>:<to>

Two things about that URL matter and are easy to get wrong:

- **`freq=Y` is required.** Without it — or with `freq=A`, which looks more
  like "annual" — the page falls back to a fixed window of the most recent
  twelve years and silently ignores `period`. With it, the full history comes
  back. Every series here would have been truncated at 2014 otherwise.
- **`period` is `from:to`, not two parameters.** `sDate`/`eDate`/`freqFrm`
  are ignored.

Indicators are addressed by two codes. `idx_cd` is the indicator, `stts_cd`
the table within it; in practice `stts_cd` is `idx_cd` with a two-digit table
number appended. Both are visible in the URL of the indicator's own page.

Several of these indicators carry more than one series under one name,
because the underlying survey changed. Those come back as separate columns
and are never spliced — see data/SOURCES.yaml.

Outputs:
  data/social/gini.csv            year,hfws,hies
  data/social/poverty.csv         year,relative,elderly_65,elderly_65_market
  data/social/mortality.csv       year,suicide,transport,pneumonia,cancer,heart,liver,diabetes,all_causes,cerebrovascular
  data/social/road.csv            year,road_rate
  data/social/vital.csv           year,births,deaths,natural_change,tfr,life_expectancy,crude_birth_rate,crude_death_rate
  data/social/migration_check.csv year,arrivals,departures,net
  data/social/workplace.csv       year,injury_rate,fatal_rate,deaths,disease_cases
  data/fiscal/debt.csv            year,d1,d2
"""
from __future__ import annotations

import html
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache"
CACHE.mkdir(exist_ok=True)

TABLE = ("https://www.index.go.kr/unity/potal/eNara/sub/showStblGams3.do"
         "?stts_cd={stts}&idx_cd={idx}&freq=Y&period={start}:{end}")
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) korea-reports/1.0"}

START, END = 2000, 2026

# indicator -> (stts_cd, idx_cd). The comment is the portal's own label.
INDICATORS = {
    "gini": ("422501", "4225"),             # 지니계수
    "poverty": ("505601", "5056"),          # 상대적 빈곤율, whole population
    "poverty_old": ("102401", "1024"),      # 노인 빈곤율, by survey and income
    "mortality": ("101201", "1012"),        # 사망원인별 사망률 추이
    "road": ("426101", "4261"),             # 도로교통사고 사망률
    "vital": ("101101", "1011"),            # 출생 사망 추이
    "migration": ("101401", "1014"),        # 국제인구이동 (입국, 출국, 순이동)
    "workplace": ("151401", "1514"),        # 산업재해현황
    "debt_d1": ("420901", "1106"),          # GDP 대비 국가채무 비율 (D1)
    "debt_d2": ("501801", "5018"),          # GDP 대비 일반정부부채 비율 (D2)
}

# A value cell that is not a number. The portal writes a dash for a year the
# series does not cover and "..." for one not yet published.
BLANK = {"-", "", "...", "..", "n/a"}


def fetch(name: str, stts: str, idx: str) -> list[list[str]]:
    """The indicator's table as a list of rows, first row the years."""
    cache_file = CACHE / f"indexkr_{name}.html"
    if cache_file.exists():
        page = cache_file.read_text()
    else:
        url = TABLE.format(stts=stts, idx=idx, start=START, end=END)
        page = ""
        for attempt in range(4):
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=60) as r:
                    page = r.read().decode("utf-8", "replace")
                break
            except Exception as e:  # noqa: BLE001
                print(f"    retry {attempt + 1}: {e}", file=sys.stderr)
                time.sleep(2 * (attempt + 1))
        if not page:
            return []
        cache_file.write_text(page)

    body = re.sub(r"<script.*?</script>", "", page, flags=re.S)
    rows = []
    for raw in re.findall(r"<tr[^>]*>(.*?)</tr>", body, flags=re.S):
        cells = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip().replace("\xa0", " ")
                 for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", raw, flags=re.S)]
        cells = [c for c in cells if c]
        if cells:
            rows.append(cells)
    return rows


def clean(value: str) -> str:
    """A value cell as a bare number, or "" if it is not one.

    The thousands comma has to go: it would split the field in the CSV this
    writes. Returning "" for anything non-numeric is what stops a label row
    being read as data — which is how a farmland series once arrived in the
    public-debt file, plausible-looking and completely wrong.
    """
    text = value.strip().replace(",", "")
    if text in BLANK:
        return ""
    try:
        float(text)
    except ValueError:
        return ""
    return text


def as_series(rows: list[list[str]], label: str | None = None,
              after: str | None = None) -> dict[int, str]:
    """{year: value} for one series of a fetched table, in either layout.

    The portal uses two: years across the top with one row per series, or
    years down the first column with one column per series. Which one you get
    is a property of the indicator, not a parameter, so both are handled.

    In the wide layout a data row is aligned to the years from the *right*:
    the portal drops a label cell when a row inherits the one above it, and
    aligning from the left would shift every value by one year.

    That dropped cell is also why `after` exists. A table grouped by survey
    prints the group name only on the group's first row, so the same `label`
    appears once per group and the rows are told apart only by which group
    they follow. `after` skips ahead to the group's heading first. Without it
    the elderly-poverty table silently returns the discontinued household
    survey instead of the current one — both plausible, ten points apart.
    """
    if not rows:
        return {}

    years = [int(c) for c in rows[0] if c.isdigit() and len(c) == 4]
    if years:  # wide: years across the header
        body = rows[1:]
        if after:
            start = next((i for i, r in enumerate(body)
                          if any(after in c for c in r)), None)
            if start is None:
                return {}
            body = body[start:]
        for row in body:
            if label and not any(label in c for c in row):
                continue
            values = row[-len(years):]
            if len(values) != len(years):
                continue
            series = {y: clean(v) for y, v in zip(years, values)}
            if any(series.values()):
                return {y: v for y, v in series.items() if v}
        return {}

    # tall: years down the first column. The series is picked by the position
    # of `label` in whichever header row names the columns.
    column = 1
    if label:
        header = next((r for r in rows if any(label in c for c in r)), None)
        if header is None:
            return {}
        column = next(i for i, c in enumerate(header) if label in c)
        # A data row starts with its year. The header row sometimes names
        # that column ("연도") and sometimes leaves the cell out entirely,
        # and in the second case its columns sit one to the left of the same
        # column in a data row. Deciding by the *width* of the two rows is
        # what tells them apart; deciding by whether the first header cell
        # is a number mistakes a named year column for a dropped one and
        # silently returns the series next to the one asked for.
        body = next((r for r in rows
                     if r and r[0].isdigit() and len(r[0]) == 4), None)
        if body is not None and len(header) < len(body):
            column += len(body) - len(header)
    out = {}
    for row in rows:
        if not row or not (row[0].isdigit() and len(row[0]) == 4):
            continue
        if column < len(row):
            value = clean(row[column])
            if value:
                out[int(row[0])] = value
    return out


def write(rel: str, header: str, years: list[int],
          columns: list[dict[int, str]]) -> None:
    path = DATA / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [header]
    for y in years:
        lines.append(f"{y}," + ",".join(c.get(y, "") for c in columns))
    path.write_text("\n".join(lines) + "\n")
    have = sum(1 for y in years if any(c.get(y) for c in columns))
    print(f"  -> data/{rel} ({have} years with data)")


def main() -> None:
    print("Fetching index.go.kr indicator tables...")
    tables = {name: fetch(name, stts, idx)
              for name, (stts, idx) in INDICATORS.items()}
    years = list(range(2006, END + 1))

    # Gini carries both surveys: 가계금융복지조사 (2011 on, the current basis)
    # and the discontinued 가계동향조사. Different universes, separate columns.
    gini = tables["gini"]
    write("social/gini.csv", "year,hfws,hies", years,
          [as_series(gini, "가계금융복지"), as_series(gini, "가계동향")])

    # Poverty comes from two indicator pages because the portal splits them,
    # but both are the same survey (가계금융복지조사) on the same basis, so
    # they sit in one file. Three columns rather than two: the market-income
    # rate next to the disposable-income rate is the size of the transfer
    # system, and in 2024 it is the difference between 54.9% and 35.9%.
    #
    # The age base is 65 and over throughout. The retirement-age base (66 and
    # over) is the one Statistics Korea headlines and the one the OECD
    # comparison uses, it is two points higher, and the two get quoted
    # interchangeably. Mixing them would be invisible and wrong.
    old = tables["poverty_old"]
    write("social/poverty.csv",
          "year,relative,elderly_65,elderly_65_market", years,
          [as_series(tables["poverty"], "상대적 빈곤율"),
           as_series(old, "처분가능소득", after="가계금융복지조사"),
           as_series(old, "시장소득", after="가계금융복지조사")])

    # One table carries every cause as a rate per 100,000, annually, back to
    # 1983. It is the same Causes of Death release the standalone 자살률
    # indicator draws on, but published a year ahead of it and without the
    # single-cause framing, so the whole panel comes from one consistent cut.
    #
    # The labels are matched on their own prefix because the portal indents
    # subordinate causes with "- " and "* ": "- 폐렴" is a component of
    # 호흡기계통의 질환 and "* 폐암" a component of 각종 암.
    mort = tables["mortality"]
    #
    # `all_causes` is the table's own 전체 row, the crude death rate on the
    # release's denominator — 주민등록 연앙인구, the mid-year registered
    # population of Korean nationals, which is also the scope of the deaths
    # counted. It is what lets a count from the same release (homicide) be
    # put on that same denominator: deaths ÷ (all_causes / 100,000).
    all_causes = as_series(mort, "전체")
    assert all_causes.get(2024) == "702.6", all_causes.get(2024)
    write("social/mortality.csv",
          "year,suicide,transport,pneumonia,cancer,heart,liver,diabetes,"
          "all_causes,cerebrovascular", years,
          [as_series(mort, "자살"), as_series(mort, "운수사고"),
           as_series(mort, "폐렴"), as_series(mort, "각종 암"),
           as_series(mort, "심장 질환"), as_series(mort, "간 질환"),
           as_series(mort, "당뇨병"), all_causes,
           as_series(mort, "뇌혈관 질환")])

    # Births and deaths on the confirmed registration basis, which is what
    # the Causes of Death release uses: 2025 deaths are 362,968 here and
    # 363,400 in the provisional February release. Natural change is computed
    # rather than read, so it cannot disagree with the two columns above it.
    vital = tables["vital"]
    births = as_series(vital, "출생아수")
    deaths = as_series(vital, "사망자수")
    change = {y: str(int(births[y]) - int(deaths[y]))
              for y in sorted(set(births) & set(deaths))}
    # The crude rates are the published ones, per 1,000, on the same
    # registered-population denominator as the Causes of Death release.
    cbr, cdr = as_series(vital, "조출생률"), as_series(vital, "조사망률")
    assert (cbr.get(2023), cdr.get(2023)) == ("4.5", "6.9"), (cbr.get(2023),
                                                              cdr.get(2023))
    write("social/vital.csv",
          "year,births,deaths,natural_change,tfr,life_expectancy,"
          "crude_birth_rate,crude_death_rate", years,
          [births, deaths, change, as_series(vital, "합계출산율"),
           as_series(vital, "기대수명"), cbr, cdr])

    # International migration, Korean nationals and foreigners together:
    # the first 입국자/출국자/순이동 rows of the table are the 계 (total)
    # group, ahead of the 내국인 and 외국인 groups.
    mig = tables["migration"]
    net = as_series(mig, "순이동")
    assert net.get(2023) == "121309", net.get(2023)
    # Review sidecar: migration is now consumed by its own chapter and must
    # never be silently revised under a published plate.  The dedicated
    # fetch_migration.py also validates the citizenship components and stock.
    write("social/migration_check.csv", "year,arrivals,departures,net", years,
          [as_series(mig, "입국자"), as_series(mig, "출국자"), net])

    # Two different road-death counts exist and are not interchangeable. The
    # police one below counts deaths on the road within 30 days of the crash;
    # the 운수사고 column of mortality.csv is a cause-of-death category that
    # also covers rail, water and air. Police 2025: 4.9 per 100k against the
    # cause-of-death 6.5. Each panel says which it draws.
    write("social/road.csv", "year,road_rate", years,
          [as_series(tables["road"])])

    # The workplace series is the clearest case on the site of a rate and a
    # count telling opposite stories: the fatal-accident rate per 10,000
    # workers more than halved while the number of deaths did not fall at all,
    # because the workforce grew and because the deaths now counted include
    # occupational disease, whose case count has more than tripled.
    work = tables["workplace"]
    write("social/workplace.csv",
          "year,injury_rate,fatal_rate,deaths,disease_cases", years,
          [as_series(work, "전체 재해율"), as_series(work, "사고성 사망만인율"),
           as_series(work, "사망자수"), as_series(work, "업무상 질병자수")])

    write("fiscal/debt.csv", "year,d1,d2", years,
          [as_series(tables["debt_d1"]), as_series(tables["debt_d2"])])


if __name__ == "__main__":
    main()
