"""The south-korea plates.

Each function draws one plate from this country's committed CSVs and saves it
through the context, which resolves every path under countries/south-korea/ and
knows this country's palette, year span and last complete year. Ported from
the standalone south-korea-reports scripts/charts.py; the drawing is unchanged.
"""
from __future__ import annotations

import csv

import matplotlib.ticker as mticker
import numpy as np


# The colour tables. Functions rather than module constants because the
# palette belongs to the country the context carries, and a module-level
# table would have to reach for it at import time.

def _spend_functions(ctx):
    """(csv column, label, colour) for the spending-by-function panel."""
    p = ctx.p
    return [
        ("social_protection", "Social protection", p.BLUE),
        ("health", "Health", p.TEAL),
        ("education", "Education", p.YELLOW),
        ("economic_affairs", "Economic affairs", p.PURPLE),
        ("general_public", "General public services", p.MUTED),
        ("defence", "Defence", p.NAVY),
        ("public_order", "Public order & safety", p.RED),
        ("other", "Other functions", p.FAINT),
    ]


def _export_products(ctx):
    p = ctx.p
    return [
        ("semiconductors", "Semiconductors", p.BLUE),
        ("cars", "Cars", p.RED),
        ("petroleum", "Petroleum products", p.YELLOW),
        ("petrochemicals", "Petrochemicals", p.PURPLE),
        ("ships", "Ships", p.TEAL),
        ("steel", "Steel", p.NAVY),
        ("car_parts", "Car parts", p.MUTED),
        ("telecom", "Phones & telecom gear", p.FAINT),
    ]


def _partners(ctx):
    p = ctx.p
    return [("China", p.RED), ("United States", p.BLUE),
            ("Vietnam", p.TEAL), ("Japan", p.PURPLE)]


def _fmt_krw(v: float) -> str:
    """Compact KRW trillions: 2677 -> '2,677tn won'. core.i18n turns the
    'tn' into 조 for a Korean reader and 'tri' for a Portuguese one."""
    return f"₩{v:,.0f}tn"


def _read(ctx, rel: str) -> list[dict[str, str]]:
    # Resolved under countries/south-korea/data, and refused otherwise.
    path = ctx.c.data(rel)
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))

def _series(ctx, rel: str, column: str, key: str = "year") -> dict[int, float]:
    """{year: value} for one column, skipping blanks.

    A blank is a year the publisher has not covered, and it stays a gap: the
    plates draw holes rather than interpolating across them.
    """
    out = {}
    for row in _read(ctx, rel):
        raw = (row.get(column) or "").strip()
        if not raw:
            continue
        try:
            out[int(row[key])] = float(raw)
        except ValueError:
            continue
    return out

def _xy(data: dict[int, float], years=None) -> tuple[list[int], list[float]]:
    years = sorted(data) if years is None else [y for y in years if y in data]
    return years, [data[y] for y in years]

def _last(data: dict[int, float]) -> tuple[int, float] | tuple[None, None]:
    if not data:
        return None, None
    year = max(data)
    return year, data[year]

def _empty(ctx, ax, note: str = "data pending — run fetchers / add CSV") -> None:
    ax.text(0.5, 0.5, note, transform=ax.transAxes, ha="center", va="center",
            fontsize=10, color=ctx.p.FAINT, style="italic")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.grid(False)

def _pct_axis(ax, decimals: int = 0) -> None:
    ax.yaxis.set_major_formatter(
        mticker.StrMethodFormatter(f"{{x:,.{decimals}f}}%"))

def _end_label(ctx, ax, data: dict[int, float], text: str | None = None,
               color=None, offset=(6, -4), fontsize=9) -> None:
    """Put the last value at the end of its own line.

    Legends cost the reader a lookup. Where a panel has room, the series is
    named and valued where it ends instead.
    """
    color = color or ctx.p.INK
    year, value = _last(data)
    if year is None:
        return
    ax.annotate(text if text is not None else f"{value:,.1f}", (year, value),
                textcoords="offset points", xytext=offset, fontsize=fontsize,
                fontweight="bold", color=color, ha="left", va="center",
                zorder=7, clip_on=False)

def _room(ax, pad: float = 2.8) -> None:
    """Widen the x axis so an `end_label` has somewhere to sit.

    Called last in a panel, after every other xlim, because it works on
    whatever range the panel ended up with rather than on a fixed one.
    """
    lo, hi = ax.get_xlim()
    ax.set_xlim(lo, hi + pad)

def _recession_bands(ctx, ax, labels: bool = True) -> None:
    for start, end, label in ctx.c.recessions:
        ax.axvspan(start, end, color=ctx.p.BAND, zorder=0)
        if labels:
            ax.text((start + end) / 2, 1.0, label,
                    transform=ax.get_xaxis_transform(), ha="center",
                    va="bottom", fontsize=7.6, color=ctx.p.MUTED, style="italic",
                    clip_on=False)

def _signed_bars(ctx, ax, data: dict[int, float]):
    years, values = _xy(data)
    colors = [ctx.p.BLUE if v >= 0 else ctx.p.RED for v in values]
    bars = ax.bar(years, values, width=0.68, color=colors, zorder=3)
    ax.axhline(0, color=ctx.p.INK, lw=0.9, zorder=4)
    return bars

def plate_economy(ctx) -> None:
    gdp = _read(ctx, "macro/gdp.csv")
    if not gdp:
        return
    nominal = _series(ctx, "macro/gdp.csv", "nominal_krw_tn")
    growth = _series(ctx, "macro/gdp.csv", "real_growth")
    percap = _series(ctx, "macro/gdp.csv", "gdp_per_capita_usd")
    cpi = _series(ctx, "macro/cpi.csv", "value")

    fig = ctx.fig(
        "The Korean Economy, 2006–2026",
        "Nominal size, real growth, income per person and inflation — the "
        "four numbers that frame everything else.",
        source="Sources: Bank of Korea ECOS — national accounts, consumer "
               "prices")

    # ---- nominal GDP
    ax = fig.next_panel("GDP — nominal size (₩ trillion)")
    years, values = _xy(nominal)
    ax.bar(years, values, width=0.68, color=ctx.p.BLUE, zorder=3)
    fig.style_axis(ax)
    ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
    year, value = _last(nominal)
    ctx.annotate_value(ax, year, value, _fmt_krw(value), color=ctx.p.BLUE_D)
    ax.set_ylim(0, max(values) * 1.18)

    # ---- real growth
    ax = fig.next_panel("Real GDP growth (% per year)")
    _signed_bars(ctx, ax, growth)
    fig.style_axis(ax)
    _pct_axis(ax, 0)
    _recession_bands(ctx, ax, labels=False)
    low_year = min(growth, key=lambda y: growth[y]) if growth else None
    if low_year is not None:
        # In the empty strip just right of the only negative bar, at its own
        # depth — the one place in this panel that is both free and adjacent.
        ax.annotate("COVID: the only contraction",
                    (low_year + 0.5, growth[low_year] * 0.6),
                    textcoords="offset points", xytext=(4, 0), fontsize=8,
                    color=ctx.p.RED, ha="left", va="center")
    if 2023 in growth:
        top = max(growth.values()) * 0.88
        ax.plot([2023, 2023], [growth[2023] + 0.25, top - 0.25],
                color=ctx.p.FAINT, lw=0.8, ls=(0, (3, 3)), zorder=2)
        ax.annotate("semiconductor cycle", (2023, top),
                    textcoords="offset points", xytext=(0, 2), fontsize=8,
                    color=ctx.p.MUTED, ha="center", va="bottom")

    # ---- GDP per capita
    ax = fig.next_panel("GDP per capita (US$, current)")
    years, values = _xy(percap)
    ax.fill_between(years, values, color=ctx.p.BLUE, alpha=0.12, zorder=2)
    ax.plot(years, values, color=ctx.p.BLUE, lw=2.4, zorder=3)
    fig.style_axis(ax)
    ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
    year, value = _last(percap)
    ctx.annotate_value(ax, year, value, f"US$ {value:,.0f}", color=ctx.p.BLUE_D,
                   ha="right", offset=(-4, 8))
    ax.set_ylim(0, max(values) * 1.2)

    # ---- inflation
    ax = fig.next_panel("Inflation — CPI (% per year) vs the 2% target")
    years, values = _xy(cpi)
    ax.axhline(2.0, color=ctx.p.TEAL, lw=1.3, ls=(0, (5, 3)), zorder=2)
    ax.annotate("target 2.0% (since 2019)", (ctx.YEARS[0] + 0.3, 2.0),
                textcoords="offset points", xytext=(0, 5), fontsize=8,
                color=ctx.p.TEAL, va="bottom", ha="left")
    ax.plot(years, values, color=ctx.p.RED, lw=2.4, zorder=4)
    ax.fill_between(years, 2.0, values, where=[v >= 2.0 for v in values],
                    color=ctx.p.RED, alpha=0.12, interpolate=True, zorder=1)
    fig.style_axis(ax)
    _pct_axis(ax, 0)
    _end_label(ctx, ax, cpi, f"{values[-1]:.1f}%", color=ctx.p.RED)
    ax.set_ylim(0, max(values) * 1.3)
    _room(ax, 2.0)

    fig.save(ctx.out("01_economy.png"))

def plate_fiscal(ctx) -> None:
    tax = _series(ctx, "fiscal/tax_burden.csv", "value")
    revenue = _series(ctx, "fiscal/government.csv", "revenue")
    spending = _series(ctx, "fiscal/government.csv", "expenditure")
    balance = _series(ctx, "fiscal/government.csv", "balance")
    d1 = _series(ctx, "fiscal/debt.csv", "d1")
    d2 = _series(ctx, "fiscal/debt.csv", "d2")
    if not tax and not d1:
        return

    fig = ctx.fig(
        "Taxes, Fiscal Balance & Public Debt, 2006–2026",
        "How much of the economy the state collects, whether it spends more "
        "than it raises, and what that does to debt — all relative to GDP.",
        source="Sources: Bank of Korea ECOS (SNA) · MOEF / e-National "
               "Indicators (D1, D2)")

    # ---- tax burden
    ax = fig.next_panel("Tax burden — tax revenue (% of GDP)")
    years, values = _xy(tax)
    ax.fill_between(years, values, color=ctx.p.BLUE, alpha=0.12, zorder=2)
    ax.plot(years, values, color=ctx.p.BLUE, lw=2.4, zorder=3)
    fig.style_axis(ax)
    _pct_axis(ax, 0)
    _end_label(ctx, ax, tax, color=ctx.p.BLUE_D)
    ax.set_ylim(0, (max(values) if values else 1) * 1.25)
    _room(ax)

    # ---- revenue against spending, with the gap drawn as the gap
    ax = fig.next_panel("Revenue vs spending (% of GDP) — the gap is the "
                        "balance")
    yr, rv = _xy(revenue)
    ys, sv = _xy(spending)
    common = [y for y in yr if y in spending]
    if common:
        rr = [revenue[y] for y in common]
        ss = [spending[y] for y in common]
        ax.fill_between(common, rr, ss, where=[a >= b for a, b in zip(rr, ss)],
                        color=ctx.p.BLUE, alpha=0.18, interpolate=True, zorder=1)
        ax.fill_between(common, rr, ss, where=[a < b for a, b in zip(rr, ss)],
                        color=ctx.p.RED, alpha=0.18, interpolate=True, zorder=1)
    ax.plot(yr, rv, color=ctx.p.BLUE, lw=2.2, zorder=3)
    ax.plot(ys, sv, color=ctx.p.RED, lw=2.2, zorder=3)
    _end_label(ctx, ax, revenue, "Revenue", color=ctx.p.BLUE_D, offset=(6, 6))
    _end_label(ctx, ax, spending, "Spending", color=ctx.p.RED, offset=(6, -8))
    fig.style_axis(ax)
    _pct_axis(ax, 0)
    _room(ax)

    # ---- balance
    ax = fig.next_panel("General government balance (% of GDP)")
    _signed_bars(ctx, ax, balance)
    fig.style_axis(ax)
    _pct_axis(ax, 0)
    low = min(balance, key=lambda y: balance[y]) if balance else None
    if low is not None:
        ax.annotate("2020: pandemic spending", (low + 0.45, balance[low] * 0.6),
                    textcoords="offset points", xytext=(4, 0), fontsize=8,
                    color=ctx.p.RED, ha="left", va="center")

    # ---- the two debt definitions, with the caption at the lines
    ax = fig.next_panel("Public debt — two official definitions (% of GDP)")
    y1, v1 = _xy(d1)
    y2, v2 = _xy(d2)
    # D2 contains D1, so it is drawn as the outer band and D1 filled inside
    # it: the reader should see one measure sitting inside the other rather
    # than read a legend to find out.
    if y2:
        ax.fill_between(y2, v2, color=ctx.p.BLUE, alpha=0.10, zorder=1)
        ax.plot(y2, v2, color=ctx.p.BLUE, lw=2.2, zorder=3)
    if y1:
        ax.fill_between(y1, v1, color=ctx.p.BLUE_D, alpha=0.20, zorder=2)
        ax.plot(y1, v1, color=ctx.p.BLUE_D, lw=2.4, zorder=4)
    _end_label(ctx, ax, d2, "D2", color=ctx.p.BLUE, offset=(6, 8))
    _end_label(ctx, ax, d1, "D1", color=ctx.p.BLUE_D, offset=(6, -8))
    if y1 and y2:
        mid = y1[len(y1) // 3]
        ax.annotate("D1 counts the central and local governments;",
                    (mid, d1.get(mid, 30)), textcoords="offset points",
                    xytext=(0, -16), fontsize=7.8, color=ctx.p.MUTED, ha="left",
                    va="top")
        ax.annotate("D2 adds the non-profit public institutions",
                    (mid, d1.get(mid, 30)), textcoords="offset points",
                    xytext=(0, -26), fontsize=7.8, color=ctx.p.MUTED, ha="left",
                    va="top")
    fig.style_axis(ax)
    _pct_axis(ax, 0)
    ax.set_ylim(0, max(v1 + v2 or [1]) * 1.25)
    _room(ax, 1.8)

    fig.save(ctx.out("02_fiscal.png"))

def plate_spending(ctx) -> None:
    rows = _read(ctx, "fiscal/spending_by_function.csv")
    if not rows:
        return
    cols = {key: _series(ctx, "fiscal/spending_by_function.csv", key)
            for key, _, _ in _spend_functions(ctx)}
    social = cols["social_protection"]
    total = _series(ctx, "fiscal/spending_by_function.csv", "total")
    invest = _series(ctx, "fiscal/investment.csv", "gfcf_pct_gdp")
    rnd = _series(ctx, "fiscal/rnd.csv", "value")

    fig = ctx.fig(
        "Where the Money Goes — Government Spending by Function, 2006–2024",
        "General government outlays by area (as % of GDP), against the "
        "investment the same budget pays for.",
        source="Sources: Bank of Korea ECOS — general government by COFOG "
               "function · World Bank (R&D)")

    # ---- stacked composition
    ax = fig.next_panel("Government spending by function (% of GDP)")
    years = sorted(set.intersection(*[set(c) for c in cols.values()]))
    base = np.zeros(len(years))
    for key, label, color in _spend_functions(ctx):
        values = np.array([cols[key][y] for y in years])
        ax.fill_between(years, base, base + values, color=color, alpha=0.85,
                        lw=0, zorder=2, label=label)
        # name each band inside itself, at the last year, where there is room
        if values[-1] > 1.6:
            ax.text(years[-1] + 0.25, base[-1] + values[-1] / 2, label,
                    fontsize=7.8, color=color, va="center", ha="left",
                    clip_on=False)
        base = base + values
    fig.style_axis(ax)
    _pct_axis(ax, 0)
    ax.set_xlim(ctx.YEARS[0] - 0.6, ctx.YEARS[-1] + 2.2)
    ax.set_ylim(0, base.max() * 1.1)

    # ---- social protection against everything else
    ax = fig.next_panel("Social protection vs everything else (% of GDP)")
    years = sorted(set(social) & set(total))
    others = {y: total[y] - social[y] for y in years}
    ax.plot(years, [social[y] for y in years], color=ctx.p.BLUE, lw=2.6, zorder=4)
    ax.plot(years, [others[y] for y in years], color=ctx.p.MUTED, lw=2.0,
            ls=(0, (6, 3)), zorder=3)
    _end_label(ctx, ax, social, "Social protection", color=ctx.p.BLUE_D, offset=(6, -4))
    _end_label(ctx, ax, others, "All other functions", color=ctx.p.MUTED, offset=(6, -4))
    fig.style_axis(ax)
    _pct_axis(ax, 0)
    ax.set_ylim(0, max(others.values()) * 1.22 if others else 1)
    _room(ax, 4.6)

    # ---- investment
    ax = fig.next_panel("Investment rate — whole economy (% of GDP)")
    years, values = _xy(invest)
    if years:
        ax.fill_between(years, values, color=ctx.p.PURPLE, alpha=0.12, zorder=2)
        ax.plot(years, values, color=ctx.p.PURPLE, lw=2.4, zorder=3)
        _end_label(ctx, ax, invest, color=ctx.p.PURPLE)
        ax.set_ylim(0, max(values) * 1.2)
        _room(ax)
    else:
        _empty(ctx, ax)
    fig.style_axis(ax)
    _pct_axis(ax, 0)

    # ---- R&D
    ax = fig.next_panel("Research & development spending (% of GDP)")
    years, values = _xy(rnd)
    if years:
        ax.fill_between(years, values, color=ctx.p.TEAL, alpha=0.14, zorder=2)
        ax.plot(years, values, color=ctx.p.TEAL, lw=2.4, zorder=3)
        _end_label(ctx, ax, rnd, f"{values[-1]:.2f}%", color=ctx.p.TEAL)
        ax.annotate("second only to Israel", (years[-1], values[-1]),
                    textcoords="offset points", xytext=(-10, -24),
                    fontsize=8, color=ctx.p.MUTED, ha="right", va="top")
        ax.set_ylim(0, max(values) * 1.25)
        _room(ax)
    else:
        _empty(ctx, ax)
    fig.style_axis(ax)
    _pct_axis(ax, 0)

    fig.save(ctx.out("03_spending.png"))

def plate_trade(ctx) -> None:
    exports = _series(ctx, "trade/trade.csv", "exports")
    imports = _series(ctx, "trade/trade.csv", "imports")
    balance = _series(ctx, "trade/trade.csv", "balance")
    if not exports:
        return

    fig = ctx.fig(
        "Foreign Trade — Exports, Imports & the Surplus, 2006–2026",
        "A manufacturing exporter the size of its own economy: "
        "semiconductors, cars and ships against an import bill that is "
        "mostly energy. 2026 = Jan–Sep.",
        source="Sources: Bank of Korea ECOS over Korea Customs Service · "
               "MOTIE releases (partial 2026) · UN Comtrade (HS headings)")

    # ---- exports and imports
    ax = fig.next_panel("Exports vs imports (US$ billion)")
    ye, ve = _xy(exports)
    yi, vi = _xy(imports)
    ax.plot(ye, ve, color=ctx.p.BLUE, lw=2.6, zorder=4)
    ax.plot(yi, vi, color=ctx.p.RED, lw=2.2, zorder=3)
    common = [y for y in ye if y in imports]
    ax.fill_between(common, [exports[y] for y in common],
                    [imports[y] for y in common], color=ctx.p.BLUE, alpha=0.10,
                    zorder=1)
    _end_label(ctx, ax, exports, "Exports", color=ctx.p.BLUE_D, offset=(6, 6))
    _end_label(ctx, ax, imports, "Imports", color=ctx.p.RED, offset=(6, -8))
    ax.set_xlim(ctx.YEARS[0] - 0.6, ctx.YEARS[-1] + 0.6)
    fig.style_axis(ax)
    ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
    fig.mark_partial(ax, 2026, "YTD Sep")
    ax.set_ylim(0, max(ve) * 1.18)
    _room(ax, 2.2)

    # ---- the balance
    ax = fig.next_panel("Trade balance (US$ billion)")
    _signed_bars(ctx, ax, balance)
    fig.style_axis(ax)
    ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
    low = min(balance, key=lambda y: balance[y]) if balance else None
    if low is not None and balance[low] < 0:
        # To the right of the deficit bar, at its own level: the caption is
        # about that bar and nothing else is drawn there.
        ax.annotate("2022: the energy bill broke the surplus",
                    (low - 0.45, balance[low] * 0.7),
                    textcoords="offset points", xytext=(-4, 0), fontsize=8,
                    color=ctx.p.RED, ha="right", va="center")
    fig.mark_partial(ax, 2026, "YTD Sep")

    # ---- export products, at five snapshot years
    ax = fig.next_panel("What Korea exports — top groups (US$ bn)")
    rows = _read(ctx, "trade/exports_products.csv")
    if rows:
        snapshots = sorted({int(r["year"]) for r in rows})
        values = {(int(r["year"]), r["product"]): float(r["usbi"])
                  for r in rows}
        width = 0.8 / len(_export_products(ctx))
        base = np.arange(len(snapshots))
        for i, (key, label, color) in enumerate(_export_products(ctx)):
            heights = [values.get((y, key), 0.0) for y in snapshots]
            ax.bar(base + i * width - 0.4 + width / 2, heights, width * 0.92,
                   color=color, zorder=3, label=label)
        ax.set_xticks(base)
        ax.set_xticklabels([str(y) for y in snapshots])
        ax.set_xlim(-0.6, len(snapshots) - 0.4)
        ax.legend(ncol=2, loc="upper left", fontsize=8, handlelength=1.1,
                  columnspacing=1.0, labelspacing=0.3)
        peak = max(values.values())
        ax.set_ylim(0, peak * 1.42)
        ax.annotate("one heading, a fifth of all exports",
                    (base[-1] - 0.4 + width / 2, values[(snapshots[-1],
                                                         "semiconductors")]),
                    textcoords="offset points", xytext=(4, 6), fontsize=8,
                    color=ctx.p.BLUE_D, ha="left", va="bottom")
        fig.style_axis(ax, xticks_years=False)
        ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
        ax.text(0.5, -0.145, "HS headings as reported by Korea — not the "
                             "ministry's MTI categories", transform=ax.transAxes,
                ha="center", va="top", fontsize=7.8, color=ctx.p.FAINT,
                style="italic")
    else:
        _empty(ctx, ax)
        fig.style_axis(ax, xticks_years=False)

    # ---- destinations
    ax = fig.next_panel("Export destinations — share of total (%)")
    rows = _read(ctx, "trade/destinations.csv")
    if rows:
        shares: dict[str, dict[int, float]] = {}
        for row in rows:
            value = (row.get("share_pct") or "").strip()
            if value:
                shares.setdefault(row["destiny"], {})[int(row["year"])] = \
                    float(value)
        for name, color in _partners(ctx):
            data = shares.get(name, {})
            if not data:
                continue
            years, values = _xy(data)
            ax.plot(years, values, color=color, lw=2.2, zorder=3)
            _end_label(ctx, ax, data, name, color=color)
        fig.style_axis(ax)
        _pct_axis(ax, 0)
        ax.set_ylim(0, 32)
        _room(ax, 3.4)
    else:
        _empty(ctx, ax)
        fig.style_axis(ax)

    fig.save(ctx.out("04_trade.png"))

def plate_markets(ctx) -> None:
    kospi = _series(ctx, "markets/kospi.csv", "close")
    sp500 = _series(ctx, "markets/sp500.csv", "close")
    won_eop = _series(ctx, "macro/won.csv", "eop")
    base_rate = _series(ctx, "macro/base_rate.csv", "value")
    cpi = _series(ctx, "macro/cpi.csv", "value")
    if not kospi:
        return

    fig = ctx.fig(
        "Money & Markets — KOSPI vs S&P 500, the Won and Interest Rates",
        "Korean equities in won, in dollars, and next to the S&P 500: the "
        "currency is half of the story.",
        source="Sources: KRX (KOSPI) · S&P (index closes) · Bank of Korea "
               "ECOS (FX, base rate, CPI)")

    def rebase(data: dict[int, float], start: int) -> dict[int, float]:
        if start not in data:
            return {}
        first = data[start]
        return {y: v / first * 100 for y, v in data.items()}

    start = min(set(kospi) & set(sp500)) if sp500 else min(kospi)

    # ---- local terms
    ax = fig.next_panel("₩100 invested in 2005 — KOSPI vs S&P 500 "
                        "(local terms)")
    k = rebase(kospi, start)
    s = rebase(sp500, start)
    for data, color, label in ((k, ctx.p.BLUE, "KOSPI (KRW)"),
                               (s, ctx.p.MUTED, "S&P 500 (USD)")):
        years, values = _xy(data)
        ax.plot(years, values, color=color, lw=2.4, zorder=3)
        _end_label(ctx, ax, data, label, color=color)
    ax.axhline(100, color=ctx.p.SPINE, lw=0.9, zorder=1)
    fig.style_axis(ax)
    ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
    ax.set_xlim(start - 0.6, ctx.YEARS[-1] + 0.6)
    _room(ax, 3.2)

    # ---- the same comparison in one currency
    ax = fig.next_panel("The same two indices in won — the exchange rate "
                        "is the difference")
    fig.style_axis(ax)
    if won_eop:
        # The exchange rate series starts a year later than the indices, so
        # this panel has its own base year. Rebasing the dollar index from
        # 2005 while the converted one could only start in 2006 silently
        # produced an empty line the first time around.
        sp_krw = {y: sp500[y] * won_eop[y] for y in sp500 if y in won_eop}
        base = min(set(sp_krw) & set(kospi))
        for data, color, label in (
                (rebase(kospi, base), ctx.p.BLUE, "KOSPI (KRW)"),
                (rebase(sp_krw, base), ctx.p.RED, "S&P 500 (in KRW)")):
            years, values = _xy(data)
            ax.plot(years, values, color=color, lw=2.4, zorder=3)
            _end_label(ctx, ax, data, label, color=color, fontsize=8)
        ax.axhline(100, color=ctx.p.SPINE, lw=0.9, zorder=1)
        ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
        ax.set_xlim(base - 0.6, ctx.YEARS[-1] + 0.6)
        _room(ax, 3.6)
    else:
        _empty(ctx, ax)

    # ---- the won
    ax = fig.next_panel("Exchange rate — KRW/USD (year-end close)")
    years, values = _xy(won_eop)
    ax.fill_between(years, values, color=ctx.p.RED, alpha=0.10, zorder=2)
    ax.plot(years, values, color=ctx.p.RED, lw=2.4, zorder=3)
    fig.style_axis(ax)
    ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
    _end_label(ctx, ax, won_eop, f"{values[-1]:,.0f}", color=ctx.p.RED)
    ax.annotate("2008-09: the won lost a third", (2009, won_eop.get(2009, 0)),
                textcoords="offset points", xytext=(6, 8), fontsize=8,
                color=ctx.p.MUTED, ha="left", va="bottom")
    ax.set_ylim(min(values) * 0.9, max(values) * 1.1)
    _room(ax, 2.2)

    # ---- policy rate against inflation
    ax = fig.next_panel("Policy rate vs inflation — BOK base rate "
                        "(year-end) vs CPI")
    yb, vb = _xy(base_rate)
    yc, vc = _xy(cpi)
    ax.plot(yb, vb, color=ctx.p.BLUE, lw=2.4, zorder=4)
    ax.plot(yc, vc, color=ctx.p.RED, lw=2.0, ls=(0, (6, 3)), zorder=3)
    _end_label(ctx, ax, base_rate, "BOK base rate", color=ctx.p.BLUE_D, offset=(6, 8))
    _end_label(ctx, ax, cpi, "CPI", color=ctx.p.RED, offset=(6, -8))
    ax.axhline(0, color=ctx.p.SPINE, lw=0.9, zorder=1)
    fig.style_axis(ax)
    _pct_axis(ax, 0)
    _room(ax, 3.6)
    fig.mark_partial(ax, 2026, "BOK base rate: level Oct")

    fig.save(ctx.out("05_markets.png"))

def plate_people(ctx) -> None:
    hdi = _series(ctx, "social/hdi.csv", "value")
    gini_hfws = _series(ctx, "social/gini.csv", "hfws")
    gini_hies = _series(ctx, "social/gini.csv", "hies")
    unemployment = _series(ctx, "macro/unemployment.csv", "value")
    wage = _series(ctx, "macro/minimum_wage.csv", "value")
    cpi = _series(ctx, "macro/cpi.csv", "value")
    relative = _series(ctx, "social/poverty.csv", "relative")
    elderly = _series(ctx, "social/poverty.csv", "elderly_65")
    elderly_market = _series(ctx, "social/poverty.csv", "elderly_65_market")

    fig = ctx.fig(
        "People — Development, Inequality, Jobs, Wages & Poverty, 2006–2026",
        "A rich country with a poor old age: high human development and low "
        "unemployment next to the OECD's worst elderly poverty.",
        ncols=3, nrows=2, figsize=(18.0, 10.2),
        source="Sources: UNDP HDR (HDI) · Statistics Korea / KOSIS (Gini, "
               "poverty, unemployment) · Minimum Wage Commission")

    # ---- HDI
    ax = fig.next_panel("Human Development Index (UNDP)")
    years, values = _xy(hdi)
    if years:
        ax.axhline(0.900, color=ctx.p.TEAL, lw=1.2, ls=(0, (5, 3)), zorder=2)
        ax.annotate("0.900 = very high development", (years[0], 0.900),
                    textcoords="offset points", xytext=(0, 5), fontsize=7.8,
                    color=ctx.p.TEAL, va="bottom", ha="left")
        ax.plot(years, values, color=ctx.p.BLUE, lw=2.4, zorder=3)
        _end_label(ctx, ax, hdi, f"{values[-1]:.3f}", color=ctx.p.BLUE_D)
        ax.set_ylim(min(values) - 0.02, max(values) + 0.02)
    else:
        _empty(ctx, ax)
    fig.style_axis(ax, n_xticks=5)
    ax.set_xticks([y for y in ctx.YEARS if y % 4 == 0])

    # ---- Gini, two surveys, never spliced
    ax = fig.next_panel("Income inequality — Gini (lower = better)")
    # Both lines are disposable-income Gini coefficients. They differ by
    # survey, not by income concept, so they are named by survey — calling
    # one of them "market income" would be a different number entirely.
    for data, color, label in (
            (gini_hfws, ctx.p.BLUE, "Household Finance & Welfare Survey"),
            (gini_hies, ctx.p.MUTED, "Household Income & Expenditure Survey")):
        years, values = _xy(data)
        if years:
            ax.plot(years, values, color=color, lw=2.3, zorder=3)
            _end_label(ctx, ax, data, label, color=color, fontsize=7.6)
    if gini_hies:
        ax.annotate("2011: new survey basis", (2011, max(gini_hfws.values())),
                    textcoords="offset points", xytext=(4, 4), fontsize=7.8,
                    color=ctx.p.MUTED, ha="left", va="bottom")
        ax.axvline(2011, color=ctx.p.FAINT, lw=0.9, ls=(0, (4, 3)), zorder=1)
    ax.text(0.5, -0.145, "two surveys, two universes — the lines are not one "
                         "series", transform=ax.transAxes, ha="center",
            va="top", fontsize=7.8, color=ctx.p.FAINT, style="italic")
    fig.style_axis(ax)
    ax.set_xticks([y for y in ctx.YEARS if y % 4 == 0])
    _room(ax, 6.0)

    # ---- unemployment
    ax = fig.next_panel("Unemployment rate (%, annual average)")
    years, values = _xy(unemployment)
    ax.fill_between(years, values, color=ctx.p.TEAL, alpha=0.12, zorder=2)
    ax.plot(years, values, color=ctx.p.TEAL, lw=2.4, zorder=3)
    _end_label(ctx, ax, unemployment, f"{values[-1]:.1f}%", color=ctx.p.TEAL)
    fig.style_axis(ax)
    _pct_axis(ax, 0)
    ax.set_xticks([y for y in ctx.YEARS if y % 4 == 0])
    ax.set_ylim(0, max(values) * 1.3)
    _room(ax, 2.6)

    # ---- minimum wage, nominal and real
    ax = fig.next_panel("Minimum wage (₩ per hour)")
    years, values = _xy(wage)
    if years and cpi:
        # Deflate with the same CPI the atlas draws, so a reader can check
        # the real line against panel 4 of plate 01 rather than take it on
        # trust. The chain runs backwards from the latest year.
        index = {}
        level = 100.0
        for year in sorted(cpi, reverse=True):
            index[year] = level
            level /= 1 + cpi[year] / 100
        real = {y: wage[y] * 100 / index[y] for y in years if y in index}
        ax.bar(years, values, width=0.68, color=ctx.p.BLUE, alpha=0.30, zorder=2)
        ry, rv = _xy(real)
        ax.plot(ry, rv, color=ctx.p.BLUE_D, lw=2.4, zorder=4)
        _end_label(ctx, ax, wage, f"₩{values[-1]:,.0f}", color=ctx.p.BLUE_D,
                  offset=(-4, 10))
        ax.text(0.03, 0.93, "In 2026 won (CPI-deflated)",
                transform=ax.transAxes, fontsize=8, color=ctx.p.BLUE_D,
                ha="left", va="top")
        ax.set_ylim(0, max(values) * 1.22)
    else:
        _empty(ctx, ax)
    fig.style_axis(ax)
    ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
    ax.set_xticks([y for y in ctx.YEARS if y % 4 == 0])

    # ---- relative poverty
    ax = fig.next_panel("Relative poverty rate (% below half median income)")
    years, values = _xy(relative)
    if years:
        ax.fill_between(years, values, color=ctx.p.PURPLE, alpha=0.12, zorder=2)
        ax.plot(years, values, color=ctx.p.PURPLE, lw=2.4, zorder=3)
        _end_label(ctx, ax, relative, f"{values[-1]:.1f}%", color=ctx.p.PURPLE)
        ax.text(0.03, 0.93, "the whole population", transform=ax.transAxes,
                fontsize=8, color=ctx.p.PURPLE, ha="left", va="top")
        ax.set_ylim(0, max(values) * 1.35)
    else:
        _empty(ctx, ax)
    fig.style_axis(ax)
    _pct_axis(ax, 0)
    ax.set_xticks([y for y in ctx.YEARS if y % 4 == 0])
    _room(ax, 2.6)

    # ---- elderly poverty, before and after transfers
    ax = fig.next_panel("Poverty at 65 and over (%)")
    ym, vm = _xy(elderly_market)
    yd, vd = _xy(elderly)
    if yd:
        # The gap between the two lines *is* the transfer system, so it is
        # shaded: the panel shows the thing it is about instead of asking the
        # reader to subtract two labelled lines.
        common = [y for y in ym if y in elderly]
        ax.fill_between(common, [elderly_market[y] for y in common],
                        [elderly[y] for y in common], color=ctx.p.YELLOW,
                        alpha=0.22, zorder=1)
        ax.plot(ym, vm, color=ctx.p.MUTED, lw=2.0, ls=(0, (6, 3)), zorder=3)
        ax.plot(yd, vd, color=ctx.p.RED, lw=2.6, zorder=4)
        _end_label(ctx, ax, elderly_market, "market income", color=ctx.p.MUTED,
                  offset=(6, 6), fontsize=8)
        _end_label(ctx, ax, elderly, "disposable income", color=ctx.p.RED,
                  offset=(6, -8), fontsize=8)
        mid = common[len(common) // 2] if common else None
        if mid is not None:
            ax.annotate("the gap is what pensions and benefits do",
                        (mid, (elderly_market[mid] + elderly[mid]) / 2),
                        textcoords="offset points", xytext=(0, 0),
                        fontsize=7.8, color=ctx.p.MUTED, ha="center", va="center")
        ax.set_ylim(0, max(vm) * 1.2)
    else:
        _empty(ctx, ax)
    fig.style_axis(ax)
    _pct_axis(ax, 0)
    ax.set_xticks([y for y in ctx.YEARS if y % 4 == 0])
    _room(ax, 5.4)

    fig.save(ctx.out("06_people.png"))

def plate_world(ctx) -> None:
    openness = _series(ctx, "intl/openness.csv", "value")
    cpi_score = _series(ctx, "intl/cpi.csv", "score")
    reserves = _series(ctx, "macro/reserves.csv", "eop_usbi")
    assets = _series(ctx, "macro/external.csv", "assets_usbi")
    liabilities = _series(ctx, "macro/external.csv", "liabilities_usbi")
    net = _series(ctx, "macro/external.csv", "net_usbi")

    fig = ctx.fig(
        "Korea in the World — Trade, Integrity & the External Balance Sheet",
        "How much of the economy rides on trade, how the outside world scores "
        "Korea for integrity, and what the country owns abroad.",
        source="Sources: World Bank — trade (% of GDP) · Transparency "
               "International — CPI · Bank of Korea ECOS (reserves, "
               "international investment position)")

    # ---- openness
    ax = fig.next_panel("Trade openness — exports + imports (% of GDP)")
    years, values = _xy(openness)
    if years:
        ax.fill_between(years, values, color=ctx.p.BLUE, alpha=0.12, zorder=2)
        ax.plot(years, values, color=ctx.p.BLUE, lw=2.4, zorder=3)
        ax.axhline(100, color=ctx.p.SPINE, lw=0.9, zorder=1)
        _end_label(ctx, ax, openness, f"{values[-1]:.0f}%", color=ctx.p.BLUE_D)
        ax.annotate("Korea trades far more than the world average",
                    (years[len(years) // 2], max(values)),
                    textcoords="offset points", xytext=(0, 10), fontsize=8,
                    color=ctx.p.MUTED, ha="center", va="bottom")
        ax.text(0.5, -0.145, "goods and services, national accounts basis",
                transform=ax.transAxes, fontsize=7.8, color=ctx.p.FAINT,
                ha="center", va="top", style="italic")
        ax.set_ylim(0, max(values) * 1.3)
        _room(ax)
    else:
        _empty(ctx, ax)
    fig.style_axis(ax)
    _pct_axis(ax, 0)

    # ---- CPI score
    ax = fig.next_panel("Corruption Perceptions Index — score "
                        "(higher = cleaner)")
    years, values = _xy(cpi_score)
    if years:
        ax.bar(years, values, width=0.68, color=ctx.p.TEAL, zorder=3)
        ctx.annotate_value(ax, years[-1], values[-1], f"{values[-1]:.0f}",
                       color=ctx.p.TEAL)
        ax.set_ylim(0, 100)
        ax.annotate("the score, not the rank: the country count changes "
                    "every year", (years[0], 88), fontsize=7.8, color=ctx.p.MUTED,
                    ha="left", va="top")
        ax.annotate("scores before 2012 used a different 0–10 scale",
                    (years[0], 80), fontsize=7.8, color=ctx.p.FAINT, ha="left",
                    va="top")
    else:
        _empty(ctx, ax)
    fig.style_axis(ax)

    # ---- reserves
    ax = fig.next_panel("Foreign exchange reserves (US$ billion, year-end)")
    years, values = _xy(reserves)
    ax.fill_between(years, values, color=ctx.p.PURPLE, alpha=0.12, zorder=2)
    ax.plot(years, values, color=ctx.p.PURPLE, lw=2.4, zorder=3)
    _end_label(ctx, ax, reserves, f"US$ {values[-1]:,.0f}bn", color=ctx.p.PURPLE)
    ax.annotate("ninth largest in the world", (years[-1], values[-1]),
                textcoords="offset points", xytext=(-6, -16), fontsize=8,
                color=ctx.p.MUTED, ha="right", va="top")
    fig.style_axis(ax)
    ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
    ax.set_ylim(0, max(values) * 1.25)
    _room(ax, 2.4)

    # ---- net external position
    ax = fig.next_panel("Net external position — assets minus liabilities "
                        "(US$ bn)")
    if net:
        ya, va = _xy(assets)
        yl, vl = _xy(liabilities)
        yn, vn = _xy(net)
        # The net line is the difference between the two above it, so the
        # difference itself is shaded and the net line drawn through it: the
        # subset relationship is visible rather than asserted.
        common = [y for y in ya if y in liabilities]
        ax.fill_between(common, [liabilities[y] for y in common],
                        [assets[y] for y in common],
                        where=[assets[y] >= liabilities[y] for y in common],
                        color=ctx.p.BLUE, alpha=0.16, interpolate=True, zorder=1)
        ax.fill_between(common, [liabilities[y] for y in common],
                        [assets[y] for y in common],
                        where=[assets[y] < liabilities[y] for y in common],
                        color=ctx.p.RED, alpha=0.16, interpolate=True, zorder=1)
        ax.plot(ya, va, color=ctx.p.BLUE, lw=1.6, zorder=3)
        ax.plot(yl, vl, color=ctx.p.MUTED, lw=1.6, zorder=3)
        ax.plot(yn, vn, color=ctx.p.BLUE_D, lw=2.8, zorder=5)
        ax.axhline(0, color=ctx.p.INK, lw=0.9, zorder=4)
        _end_label(ctx, ax, assets, "Foreign assets", color=ctx.p.BLUE, offset=(6, 6))
        _end_label(ctx, ax, liabilities, "Foreign liabilities", color=ctx.p.MUTED,
                  offset=(6, -8))
        _end_label(ctx, ax, net, "Net position", color=ctx.p.BLUE_D, offset=(6, 0))
        cross = next((y for y in yn if net[y] > 0), None)
        if cross:
            ax.annotate("2014: Korea becomes a net creditor", (cross, 0),
                        textcoords="offset points", xytext=(6, -8),
                        fontsize=8, color=ctx.p.BLUE_D, ha="left", va="top")
    else:
        _empty(ctx, ax)
    fig.style_axis(ax)
    ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
    _room(ax, 4.6)

    fig.save(ctx.out("07_world.png"))

def plate_demography(ctx) -> None:
    pop = _series(ctx, "social/population.csv", "pop_mn")
    elderly = _series(ctx, "social/population.csv", "elderly_pct")
    tfr = _series(ctx, "social/population.csv", "tfr")
    births = _series(ctx, "social/vital.csv", "births")
    deaths = _series(ctx, "social/vital.csv", "deaths")
    if not pop:
        return

    last_observed = max(births) if births else 2025

    fig = ctx.fig(
        "Korea's Demographic Transition — the Peak Has Passed",
        "The lowest fertility rate ever recorded in peacetime. The 2024 "
        "projection has the population falling for the rest of the century; "
        "dashed = projected.",
        source="Sources: Statistics Korea — Population Projections (2024 "
               "revision), Vital Statistics")

    # ---- population, observed and projected
    ax = fig.next_panel("Population (millions)")
    obs = {y: v for y, v in pop.items() if y <= last_observed}
    proj = {y: v for y, v in pop.items() if y >= last_observed}
    yo, vo = _xy(obs)
    yp, vp = _xy(proj)
    ax.fill_between(yo, vo, color=ctx.p.BLUE, alpha=0.12, zorder=2)
    ax.plot(yo, vo, color=ctx.p.BLUE, lw=2.6, zorder=4)
    ax.plot(yp, vp, color=ctx.p.BLUE, lw=2.0, ls=(0, (5, 3)), zorder=3)
    ax.fill_between(yp, vp, color=ctx.p.BLUE, alpha=0.05, zorder=1)
    peak = max(pop, key=lambda y: pop[y])
    ax.annotate(f"{pop[peak]:.1f}mn", (peak, pop[peak]),
                textcoords="offset points", xytext=(6, 15), fontsize=8.5,
                fontweight="bold", color=ctx.p.BLUE_D, ha="left", va="bottom")
    ax.annotate("the peak, 2020", (peak, pop[peak]),
                textcoords="offset points", xytext=(6, 5), fontsize=8,
                color=ctx.p.MUTED, ha="left", va="bottom")
    _end_label(ctx, ax, proj, f"{vp[-1]:.1f}mn", color=ctx.p.BLUE, offset=(-4, -14))
    ax.text(last_observed + 1, min(vp) * 1.02, "projected", fontsize=8,
            color=ctx.p.MUTED, ha="left", va="bottom", style="italic")
    fig.style_axis(ax, xticks_years=False)
    ax.set_xlim(min(pop) - 1, max(pop) + 1)
    ax.set_xticks([y for y in range(2000, 2081, 10) if y <= max(pop)])
    ax.set_ylim(0, max(pop.values()) * 1.18)
    _room(ax, 6.0)

    # ---- fertility
    ax = fig.next_panel("Total fertility rate — children per woman")
    years, values = _xy({y: v for y, v in tfr.items() if y <= last_observed})
    ax.axhline(2.1, color=ctx.p.TEAL, lw=1.2, ls=(0, (5, 3)), zorder=2)
    ax.annotate("replacement level 2.1", (years[0], 2.1),
                textcoords="offset points", xytext=(0, 5), fontsize=8,
                color=ctx.p.TEAL, va="bottom", ha="left")
    ax.plot(years, values, color=ctx.p.RED, lw=2.6, zorder=4)
    ax.fill_between(years, values, color=ctx.p.RED, alpha=0.10, zorder=2)
    trough = min(tfr, key=lambda y: tfr[y])
    ctx.annotate_value(ax, trough, tfr[trough], f"{tfr[trough]:.3f}", color=ctx.p.RED,
                   offset=(0, -16))
    _end_label(ctx, ax, {y: v for y, v in tfr.items() if y <= last_observed},
              f"{values[-1]:.3f}", color=ctx.p.RED)
    fig.style_axis(ax, xticks_years=False)
    ax.set_xticks([y for y in range(2000, 2031, 5) if y <= last_observed])
    ax.set_xlim(years[0] - 0.6, last_observed + 1.4)
    ax.set_ylim(0, 2.4)

    # ---- births and deaths
    ax = fig.next_panel("Births and deaths per year (thousands)")
    yb, vb = _xy({y: v / 1000 for y, v in births.items()})
    yd, vd = _xy({y: v / 1000 for y, v in deaths.items()})
    common = [y for y in yb if y in deaths]
    ax.fill_between(common, [births[y] / 1000 for y in common],
                    [deaths[y] / 1000 for y in common],
                    where=[births[y] >= deaths[y] for y in common],
                    color=ctx.p.BLUE, alpha=0.14, interpolate=True, zorder=1)
    ax.fill_between(common, [births[y] / 1000 for y in common],
                    [deaths[y] / 1000 for y in common],
                    where=[births[y] < deaths[y] for y in common],
                    color=ctx.p.RED, alpha=0.14, interpolate=True, zorder=1)
    ax.plot(yb, vb, color=ctx.p.BLUE, lw=2.4, zorder=3)
    ax.plot(yd, vd, color=ctx.p.RED, lw=2.4, zorder=3)
    _end_label(ctx, ax, {y: v / 1000 for y, v in births.items()}, "Births",
              color=ctx.p.BLUE_D, offset=(6, -8))
    _end_label(ctx, ax, {y: v / 1000 for y, v in deaths.items()}, "Deaths",
              color=ctx.p.RED, offset=(6, 6))
    _room(ax, 2.4)
    cross = next((y for y in common if deaths[y] > births[y]), None)
    if cross:
        level = births[cross] / 1000
        ax.annotate("deaths overtake", (cross, level),
                    textcoords="offset points", xytext=(-10, 46), fontsize=8,
                    color=ctx.p.RED, ha="right", va="bottom")
        ax.annotate("births in 2020", (cross, level),
                    textcoords="offset points", xytext=(-10, 36), fontsize=8,
                    color=ctx.p.RED, ha="right", va="bottom")
        ax.axvline(cross, color=ctx.p.FAINT, lw=0.9, ls=(0, (4, 3)), zorder=1)
    fig.style_axis(ax)
    ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
    ax.set_xlim(ctx.YEARS[0] - 0.6, last_observed + 1.6)

    # ---- ageing
    ax = fig.next_panel("Share of the population aged 65 and over (%)")
    obs = {y: v for y, v in elderly.items() if y <= last_observed}
    proj = {y: v for y, v in elderly.items() if y >= last_observed}
    yo, vo = _xy(obs)
    yp, vp = _xy(proj)
    ax.axhline(20, color=ctx.p.TEAL, lw=1.2, ls=(0, (5, 3)), zorder=2)
    ax.annotate("20% = a super-aged society", (yo[0], 20),
                textcoords="offset points", xytext=(0, 5), fontsize=8,
                color=ctx.p.TEAL, va="bottom", ha="left")
    ax.fill_between(yo, vo, color=ctx.p.RED, alpha=0.14, zorder=2)
    ax.plot(yo, vo, color=ctx.p.RED, lw=2.6, zorder=4)
    ax.plot(yp, vp, color=ctx.p.RED, lw=2.0, ls=(0, (5, 3)), zorder=3)
    ax.fill_between(yp, vp, color=ctx.p.RED, alpha=0.05, zorder=1)
    _end_label(ctx, ax, proj, f"{vp[-1]:.1f}%", color=ctx.p.RED, offset=(-4, -14))
    ctx.annotate_value(ax, last_observed, obs[last_observed],
                   f"{obs[last_observed]:.1f}%", color=ctx.p.RED, offset=(0, 10))
    fig.style_axis(ax, xticks_years=False)
    ax.set_xticks([y for y in range(2000, 2081, 10) if y <= max(elderly)])
    ax.set_xlim(min(elderly) - 1, max(elderly) + 1)
    ax.set_ylim(0, max(elderly.values()) * 1.2)
    _room(ax, 6.0)

    fig.save(ctx.out("08_demography.png"))

def plate_safety(ctx) -> None:
    suicide = _series(ctx, "social/mortality.csv", "suicide")
    pneumonia = _series(ctx, "social/mortality.csv", "pneumonia")
    homicide_n = _series(ctx, "social/homicide.csv", "deaths")
    population = _series(ctx, "macro/gdp.csv", "population_mn")
    covid_rate = _series(ctx, "social/covid.csv", "rate")
    road = _series(ctx, "social/road.csv", "road_rate")
    fatal_rate = _series(ctx, "social/workplace.csv", "fatal_rate")
    work_deaths = _series(ctx, "social/workplace.csv", "deaths")
    if not suicide:
        return

    # The release publishes homicide as a count and only to one decimal as a
    # rate, which rounds a sub-1.0 series into uselessness. Converting the
    # count with the population the rest of the atlas uses reproduces the
    # published rate and keeps the precision the panel needs.
    homicide = {y: n / population[y] / 10 for y, n in homicide_n.items()
                if y in population}

    fig = ctx.fig(
        "Health & Safety — Self-Harm, Homicide, the Pandemic, Roads & Work",
        "One of the safest countries in the world from other people, and the "
        "most dangerous in the OECD from oneself.",
        source="Sources: Statistics Korea / Ministry of Data and Statistics "
               "— Causes of Death Statistics · National Police Agency "
               "(roads) · Ministry of Employment and Labour (workplace)")

    # ---- suicide and homicide on one axis
    ax = fig.next_panel("Suicide and homicide, deaths per 100k — the same "
                        "axis")
    ys, vs = _xy(suicide)
    yh, vh = _xy(homicide)
    # No fill under suicide here. Filling it would put the homicide line
    # inside a shaded suicide area, and a line inside another line's area
    # reads as a part of it — which is exactly what these two are not.
    ax.plot(ys, vs, color=ctx.p.RED, lw=2.6, zorder=4)
    ax.plot(yh, vh, color=ctx.p.INK, lw=2.2, zorder=4)
    _end_label(ctx, ax, suicide, "Suicide", color=ctx.p.RED, offset=(6, 0))
    _end_label(ctx, ax, homicide, "Homicide", color=ctx.p.INK, offset=(6, 0))
    peak = max(suicide, key=lambda y: suicide[y])
    ctx.annotate_value(ax, peak, suicide[peak], "2011: the peak, 31.7",
                   color=ctx.p.RED, offset=(0, 8), fontsize=8, weight="normal")
    ax.annotate("the OECD's highest", (ys[-1], vs[-1]),
                textcoords="offset points", xytext=(6, -14), fontsize=8,
                color=ctx.p.MUTED, ha="left", va="top")
    # The explanation of the flat line sits at the flat line.
    if yh:
        mid = yh[len(yh) // 2]
        ax.annotate("Homicide never leaves the floor of this chart:",
                    (mid, homicide[mid]), textcoords="offset points",
                    xytext=(0, 16), fontsize=7.8, color=ctx.p.INK, ha="center",
                    va="bottom")
        ax.annotate("0.5 per 100k in 2025, against 27.8 for suicide",
                    (mid, homicide[mid]), textcoords="offset points",
                    xytext=(0, 7), fontsize=7.8, color=ctx.p.MUTED, ha="center",
                    va="bottom")
        ax.annotate("published as a count only from 2014",
                    (yh[0], homicide[yh[0]]), textcoords="offset points",
                    xytext=(-4, 10), fontsize=7.4, color=ctx.p.FAINT, ha="right",
                    va="bottom")
    fig.style_axis(ax)
    ax.set_ylim(0, max(vs) * 1.22)
    _room(ax, 2.6)

    # ---- the pandemic years
    ax = fig.next_panel("The pandemic years — COVID-19 against pneumonia, "
                        "deaths per 100k")
    yp, vp = _xy(pneumonia)
    yc, vc = _xy(covid_rate)
    ax.fill_between(yp, vp, color=ctx.p.BLUE, alpha=0.12, zorder=2)
    ax.plot(yp, vp, color=ctx.p.BLUE, lw=2.6, zorder=4)
    if yc:
        ax.bar(yc, vc, width=0.6, color=ctx.p.RED, zorder=5)
        top = max(covid_rate, key=lambda y: covid_rate[y])
        ctx.annotate_value(ax, top, covid_rate[top], f"{covid_rate[top]:.1f}",
                       color=ctx.p.RED)
        _end_label(ctx, ax, covid_rate, "COVID-19", color=ctx.p.RED, offset=(6, 0))
    _end_label(ctx, ax, pneumonia, "Pneumonia", color=ctx.p.BLUE_D, offset=(6, 0))
    if yp:
        ax.annotate("Pneumonia was already climbing before 2020 —",
                    (2015, pneumonia.get(2015, 29)),
                    textcoords="offset points", xytext=(8, -8), fontsize=7.8,
                    color=ctx.p.BLUE_D, ha="left", va="top")
        ax.annotate("an ageing population, not the pandemic",
                    (2015, pneumonia.get(2015, 29)),
                    textcoords="offset points", xytext=(8, -17), fontsize=7.8,
                    color=ctx.p.MUTED, ha="left", va="top")
    ax.text(0.5, -0.145, "counted from death certificates, not case "
                         "surveillance", transform=ax.transAxes, ha="center",
            va="top", fontsize=7.8, color=ctx.p.FAINT, style="italic")
    fig.style_axis(ax)
    ax.set_ylim(0, max(vp + vc or [1]) * 1.3)
    _room(ax, 3.0)

    # ---- roads
    ax = fig.next_panel("Road deaths per 100k — police count, within 30 days")
    years, values = _xy(road)
    ax.fill_between(years, values, color=ctx.p.TEAL, alpha=0.12, zorder=2)
    ax.plot(years, values, color=ctx.p.TEAL, lw=2.6, zorder=3)
    _end_label(ctx, ax, road, f"{values[-1]:.1f}", color=ctx.p.TEAL)
    ctx.annotate_value(ax, years[0], values[0], f"{values[0]:.1f}", color=ctx.p.TEAL,
                   offset=(0, 10))
    fig.style_axis(ax)
    ax.set_ylim(0, max(values) * 1.25)
    _room(ax)

    # ---- workplace: the rate and the count disagree, and the panel says so
    ax = fig.next_panel("Workplace deaths — the rate halved, the count "
                        "did not")
    yr, vr = _xy(fatal_rate)
    ax.plot(yr, vr, color=ctx.p.BLUE, lw=2.6, zorder=4)
    ax.fill_between(yr, vr, color=ctx.p.BLUE, alpha=0.12, zorder=2)
    ax.annotate("Fatal accident rate (per 10,000 workers)", (yr[-1], vr[-1]),
                textcoords="offset points", xytext=(-6, 14), fontsize=8,
                fontweight="bold", color=ctx.p.BLUE_D, ha="right", va="bottom")
    fig.style_axis(ax)
    ax.set_ylim(0, max(vr) * 1.35)

    twin = ax.twinx()
    yd, vd = _xy(work_deaths)
    twin.plot(yd, vd, color=ctx.p.RED, lw=2.2, ls=(0, (6, 3)), zorder=5)
    twin.set_ylim(0, max(vd) * 1.35)
    twin.spines[["top", "left", "right"]].set_visible(False)
    twin.tick_params(length=0, colors=ctx.p.RED)
    twin.grid(False)
    twin.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
    twin.annotate("Deaths (count, incl. occupational disease)",
                  (yd[-1], vd[-1]), textcoords="offset points",
                  xytext=(-6, 12), fontsize=8, fontweight="bold",
                  color=ctx.p.RED, ha="right", va="bottom")
    mid = yr[len(yr) // 2]
    ax.annotate("The rate falls because the workforce grew;",
                (mid, fatal_rate[mid]), textcoords="offset points",
                xytext=(0, -14), fontsize=7.8, color=ctx.p.BLUE_D, ha="center",
                va="top")
    ax.annotate("the count holds because these deaths now include disease",
                (mid, fatal_rate[mid]), textcoords="offset points",
                xytext=(0, -23), fontsize=7.8, color=ctx.p.MUTED, ha="center",
                va="top")

    fig.save(ctx.out("09_safety.png"))

def plate_credit(ctx) -> None:
    credit = _series(ctx, "macro/household_credit.csv", "credit_krw_tn")
    loans = _series(ctx, "macro/household_credit.csv", "loans_krw_tn")
    card = _series(ctx, "macro/household_credit.csv", "card_krw_tn")
    share = _series(ctx, "macro/household_credit.csv", "credit_pct_gdp")
    household_rate = _series(ctx, "macro/credit_terms.csv", "household_rate")
    mortgage = _series(ctx, "macro/credit_terms.csv", "mortgage_rate")
    unsecured = _series(ctx, "macro/credit_terms.csv", "unsecured_rate")
    late_house = _series(ctx, "macro/credit_terms.csv", "household_late")
    late_firms = _series(ctx, "macro/credit_terms.csv", "corporate_late")
    if not credit:
        return

    fig = ctx.fig(
        "Household Debt & the Price of Credit, 2006–2026",
        "Korean households owe almost as much as the whole economy produces "
        "in a year. What they pay for it, and how much of it goes unpaid.",
        source="Sources: Bank of Korea ECOS — household credit (flow of "
               "funds), weighted-average lending rates of deposit banks, "
               "loan delinquency rates")

    # ---- the stock, split into its two components
    ax = fig.next_panel("Household credit (₩ trillion)")
    years = sorted(set(loans) & set(card))
    lv = [loans[y] for y in years]
    cv = [card[y] for y in years]
    ax.bar(years, lv, width=0.68, color=ctx.p.BLUE, zorder=3)
    ax.bar(years, cv, width=0.68, bottom=lv, color=ctx.p.YELLOW, zorder=3)
    year, value = _last(credit)
    ctx.annotate_value(ax, year, value, _fmt_krw(value), color=ctx.p.BLUE_D)
    # Centred where every bar underneath it is tall enough to hold the text,
    # so the white label never hangs off the end of a short bar.
    tall = years[len(years) // 2 + 2]
    ax.annotate("Bank and non-bank loans", (tall, 620),
                fontsize=8.5, fontweight="bold", color=ctx.p.CARD, ha="center",
                va="center", zorder=6)
    # The yellow band is a few per cent of the bar, so it is named where it
    # is thickest and the caption sits in the clear space above the early
    # bars rather than across them.
    ax.text(0.03, 0.97, "Card and instalment credit is the thin band on top —",
            transform=ax.transAxes, fontsize=7.8, color=ctx.p.YELLOW, ha="left",
            va="top")
    ax.text(0.03, 0.925, "the debt is overwhelmingly loans",
            transform=ax.transAxes, fontsize=7.8, color=ctx.p.MUTED, ha="left",
            va="top")
    fig.style_axis(ax)
    ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
    ax.set_ylim(0, max(credit.values()) * 1.25)
    _room(ax, 1.4)

    # ---- against the size of the economy
    ax = fig.next_panel("Household credit as a share of GDP (%)")
    years, values = _xy(share)
    ax.fill_between(years, values, color=ctx.p.BLUE, alpha=0.12, zorder=2)
    ax.plot(years, values, color=ctx.p.BLUE, lw=2.6, zorder=3)
    peak = max(share, key=lambda y: share[y])
    ctx.annotate_value(ax, peak, share[peak], f"{share[peak]:.1f}%",
                   color=ctx.p.BLUE_D)
    ax.annotate("the 2021 peak", (peak, share[peak]),
                textcoords="offset points", xytext=(10, -16), fontsize=8,
                color=ctx.p.MUTED, ha="left", va="top")
    _end_label(ctx, ax, share, f"{values[-1]:.1f}%", color=ctx.p.BLUE_D)
    fig.style_axis(ax)
    _pct_axis(ax, 0)
    ax.set_ylim(0, max(values) * 1.25)
    _room(ax, 2.2)

    # ---- what credit costs
    ax = fig.next_panel("What credit costs — new bank lending rates "
                        "(% per year)")
    for data, color, label, dy in (
            (unsecured, ctx.p.RED, "Unsecured loans", 10),
            (household_rate, ctx.p.BLUE, "Household loans, all purposes", 0),
            (mortgage, ctx.p.TEAL, "Housing loans", -11)):
        years, values = _xy(data)
        if not years:
            continue
        ax.plot(years, values, color=color, lw=2.3, zorder=3)
        _end_label(ctx, ax, data, label, color=color, offset=(6, dy), fontsize=8)
    if unsecured:
        spike = max(unsecured, key=lambda y: unsecured[y] if y >= 2021 else 0)
        ax.annotate("rates double in two years", (spike, unsecured[spike]),
                    textcoords="offset points", xytext=(0, 10), fontsize=8,
                    color=ctx.p.MUTED, ha="center", va="bottom")
    fig.style_axis(ax)
    _pct_axis(ax, 0)
    ax.set_ylim(0, 12)
    _room(ax, 5.4)

    # ---- who actually falls behind
    ax = fig.next_panel("Loan delinquency — share of bank loans overdue (%)")
    for data, color, label in ((late_firms, ctx.p.MUTED, "Businesses"),
                               (late_house, ctx.p.RED, "Households")):
        years, values = _xy(data)
        if not years:
            continue
        ax.fill_between(years, values, color=color, alpha=0.10, zorder=2)
        ax.plot(years, values, color=color, lw=2.3, zorder=3)
        _end_label(ctx, ax, data, label, color=color)
    fig.style_axis(ax)
    _pct_axis(ax, 1)
    ax.set_ylim(0, 2.4)
    _room(ax, 3.0)

    fig.save(ctx.out("10_credit.png"))


# The plates, in the order the page lists them.
PLATES = (

    ("plate_economy", plate_economy),

    ("plate_fiscal", plate_fiscal),

    ("plate_spending", plate_spending),

    ("plate_trade", plate_trade),

    ("plate_markets", plate_markets),

    ("plate_people", plate_people),

    ("plate_world", plate_world),

    ("plate_demography", plate_demography),

    ("plate_safety", plate_safety),

    ("plate_credit", plate_credit),

)
