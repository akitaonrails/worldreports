"""The canada plates.

Each builder draws one plate from this country's committed CSVs. The plates
are declared in the declarative shape — id, slug, title, subtitle, alt in
PLATES — so the title and the alt text are reviewable without reading the
drawing code; core.render creates the figure and the builder only fills its
panels.

Five plates exist while Statistics Canada's platform is down: fiscal,
spending, markets, world and migration, drawn from the Department of
Finance's Fiscal Reference Tables, the Bank of Canada, IRCC's open data and
the World Bank/UNDP comparables layer. The StatCan chapters (economy, people,
demography, trade, security, mortality, credit) slot into their spine numbers
when the platform returns — see HANDOFF.md.
"""
from __future__ import annotations

import numpy as np


# ------------------------------------------------------------ small helpers
def _fy(ctx, rel: str, col: str, since: int = 0):
    """(years, values) from a fiscal-year CSV, blanks dropped.

    The FRT files are keyed by `fiscal_year` — the STARTING year of an
    April-March fiscal year — so ctx.series, which reads the `year` column,
    cannot see them. ctx.rows takes the key and skips the '#' provenance
    header.
    """
    rows = ctx.rows(rel, key="fiscal_year") or {}
    out = [(y, float(r[col])) for y, r in sorted(rows.items())
           if y >= since and (r.get(col) or "").strip()]
    return [y for y, _ in out], [v for _, v in out]


def _yr(ctx, rel: str, col: str, since: int = 0):
    """(years, values) from a calendar-year CSV, blanks dropped."""
    t = ctx.table(rel)
    if not t or col not in t:
        return [], []
    yrs, vals = ctx.series(t, col)
    keep = [(y, v) for y, v in zip(yrs, vals) if y >= since]
    return [y for y, _ in keep], [v for _, v in keep]


W0 = 2006   # the shared plate window opens here


def plate_fiscal(ctx, ig) -> None:
    p = ctx.p

    ax = ig.next_panel("Revenues and total expenses (% of GDP)")
    ry, rv = _fy(ctx, "fiscal/transactions_pct_gdp.csv", "revenues", W0)
    ey, ev = _fy(ctx, "fiscal/expenses_pct_gdp.csv", "total_expenses", W0)
    ctx.line(ax, ey, ev, p.RED, label="Total expenses")
    ctx.line(ax, ry, rv, p.NAVY, label="Revenues")
    ax.fill_between(ry, rv, ev, color=p.RED, alpha=0.10, zorder=1)
    ax.legend(loc="upper left", fontsize=8.6)
    ig.add_recessions(ax, inside=True)
    peak = max(zip(ey, ev), key=lambda t: t[1])
    ax.annotate(f"{peak[1]:.1f}%", peak, textcoords="offset points",
                xytext=(0, 8), ha="center", fontsize=9, fontweight="bold",
                color=p.RED)
    ax.text(2012.5, 24.5, "the gap is the deficit",
            fontsize=8.2, color=p.MUTED, style="italic")
    ig.headroom(ax, top=0.16)
    ax.set_ylim(10, ax.get_ylim()[1])

    ax = ig.next_panel("Budgetary balance (% of GDP)")
    by, bv = _fy(ctx, "fiscal/transactions_pct_gdp.csv", "budgetary_balance", W0)
    xy, xv = _fy(ctx, "fiscal/transactions_pct_gdp.csv",
                 "balance_excl_actuarial", W0)
    ax.axhline(0, color=p.MUTED, lw=1.0)
    ctx.bars(ax, by, bv, lambda v: p.GREEN if v >= 0 else p.RED)
    ctx.line(ax, xy, xv, p.GOLD, lw=1.8, dashed_partial=False,
             label="before net actuarial losses (2008-09 onward)")
    worst = min(zip(by, bv), key=lambda t: t[1])
    ax.annotate(f"{worst[1]:.1f}%", worst, textcoords="offset points",
                xytext=(0, -6), ha="center", va="top", fontsize=9,
                fontweight="bold", color=p.RED)
    ax.annotate("2020-21: the largest federal deficit\n"
                "in Canadian peacetime", xy=worst, xytext=(2012.4, -12.6),
                fontsize=8.2, color=p.MUTED, style="italic",
                arrowprops=dict(arrowstyle="-", color=p.FAINT, lw=0.8))
    ax.legend(loc="upper right", fontsize=8.2)
    ax.text(2006.2, -3.6, "the actuarial split does not exist before 2008-09\n"
            "and is not back-filled from the undivided balance",
            fontsize=7.6, color=p.FAINT, style="italic", va="top")
    ax.set_ylim(-16.5, 3.5)

    ax = ig.next_panel("Public debt charges (% of GDP)")
    dy, dv = _fy(ctx, "fiscal/transactions_pct_gdp.csv",
                 "public_debt_charges", W0)
    ctx.line(ax, dy, dv, p.PURPLE)
    ctx.endlabel(ax, dy, dv, p.PURPLE, lambda v: f"{v:.1f}%", dy=10)
    ig.add_recessions(ax, inside=True)
    ax.text(2013.0, 2.15, "a decade of cheap money ended in 2022:\n"
            "the interest bill is back where it was in 2008",
            fontsize=8.2, color=p.MUTED, style="italic", va="top")
    ax.set_ylim(0, 2.6)

    ax = ig.next_panel("The federal debt, two measures (C$ trillion)")
    ay, av = _fy(ctx, "fiscal/liabilities.csv", "accumulated_deficit_mn")
    ny, nv = _fy(ctx, "fiscal/liabilities.csv", "net_debt_mn")
    av = [v / 1e6 for v in av]
    nv = [v / 1e6 for v in nv]
    ctx.line(ax, ay, av, p.RED, marker="",
             label="Accumulated deficit — what budgets call “the federal debt”")
    ctx.line(ax, ny, nv, p.BLUE, marker="", dashed_partial=False,
             label="Net debt — liabilities minus financial assets")
    ax.legend(loc="upper left", fontsize=8.4)
    ax.annotate("the 1990s paydown", xy=(2000, 0.63), xytext=(1982, 0.95),
                fontsize=8.2, color=p.MUTED, style="italic",
                arrowprops=dict(arrowstyle="-", color=p.FAINT, lw=0.8))
    # Off to the left with an arrow: an endlabel at the endpoint lands on
    # the line itself, and right of it runs off the canvas in translation.
    ax.annotate(f"C${av[-1]:.2f}tn", xy=(ay[-1], av[-1]),
                xytext=(2019.8, 0.88), ha="left", va="center",
                fontsize=9.5, fontweight="bold", color=p.RED, zorder=6,
                arrowprops=dict(arrowstyle="-", color=p.RED, lw=0.8))
    ax.text(2026.4, 0.40, "neither is the general-government debt\n"
            "on the World plate — the three debts answer\n"
            "different questions and are quoted as one",
            fontsize=7.8, color=p.FAINT, style="italic", va="top",
            ha="right")
    ax.set_ylim(0, 1.5)
    # This panel leaves the shared window: the FRT run from 1966, and the
    # 1990s paydown is the story. xticks_years=False leaves the x axis
    # alone, so the ticks and the window are set here.
    ig.style_axis(ax, xticks_years=False)
    ax.set_xticks(list(range(1970, 2030, 10)))
    ax.set_xlim(1965.4, 2026.6)

    for i, a in enumerate(ig.axes_flat[:3]):
        ig.style_axis(a)
        a.set_xlim(W0 - 0.6, 2024.6)


def plate_spending(ctx, ig) -> None:
    p = ctx.p
    REL = "fiscal/expenses_pct_gdp.csv"

    ax = ig.next_panel("Expenses by category (% of GDP)")
    CATS = [("transfers_to_persons", "Transfers to persons", p.RED),
            ("transfers_to_provinces", "Transfers to provinces", p.BLUE),
            ("direct_program_expenses", "Direct program expenses", p.GOLD),
            ("public_debt_charges", "Public debt charges", p.PURPLE)]
    series = [_fy(ctx, REL, c, W0) for c, _, _ in CATS]
    yrs = series[0][0]
    stack = [s[1] for s in series]
    ax.stackplot(yrs, *stack, labels=[l for _, l, _ in CATS],
                 colors=[c for _, _, c in CATS], alpha=0.92, lw=0)
    ax.legend(loc="upper left", fontsize=8.2, ncol=2)
    ig.add_event(ax, 2020.25, "COVID-19", dy=0.97)
    ax.text(0.5, -0.125, "net actuarial losses (0.7% of GDP at most) are "
            "not drawn", transform=ax.transAxes, ha="center", fontsize=7.6,
            color=p.FAINT, style="italic")
    ax.set_ylim(0, 32)

    ax = ig.next_panel("Program expenses vs debt charges (% of GDP)")
    py_, pv = _fy(ctx, REL, "total_program_expenses", W0)
    dy, dv = _fy(ctx, REL, "public_debt_charges", W0)
    ctx.line(ax, py_, pv, p.NAVY, label="Program expenses")
    ctx.line(ax, dy, dv, p.PURPLE, label="Public debt charges")
    peak = max(zip(py_, pv), key=lambda t: t[1])
    ax.annotate(f"{peak[1]:.1f}% — the pandemic benefits", peak,
                textcoords="offset points", xytext=(-8, 10), ha="right",
                fontsize=8.6, fontweight="bold", color=p.NAVY)
    ax.legend(loc="upper left", fontsize=8.6)
    ig.add_recessions(ax, label=False)
    ax.set_ylim(0, 31)

    ax = ig.next_panel("Revenues by source (% of GDP)")
    SRC = [("personal_income_tax", "Personal income tax", p.NAVY),
           ("corporate_income_tax", "Corporate income tax", p.RED),
           ("other_taxes_and_duties", "Other taxes and duties", p.PURPLE),
           ("ei_premiums", "EI premiums", p.GOLD),
           ("other_revenues", "Other revenues", p.FAINT)]
    for col, label, color in SRC:
        sy, sv = _fy(ctx, "fiscal/revenues_pct_gdp.csv", col, W0)
        ctx.line(ax, sy, sv, color, label=label,
                 lw=1.8 if color == p.FAINT else 2.4,
                 dashed_partial=color != p.FAINT)
    ax.legend(loc="upper center", fontsize=7.4, ncol=3)
    ax.text(0.5, -0.125, "non-resident income tax (~0.4% of GDP) is not "
            "drawn; pollution-pricing proceeds are excluded — see SOURCES",
            transform=ax.transAxes, ha="center", fontsize=7.6,
            color=p.FAINT, style="italic")
    ax.set_ylim(0, 10.5)

    ax = ig.next_panel("Personal income tax vs everything else (% of GDP)")
    py2, pv2 = _fy(ctx, "fiscal/revenues_pct_gdp.csv",
                   "personal_income_tax", W0)
    ty, tv = _fy(ctx, "fiscal/revenues_pct_gdp.csv", "total_revenues", W0)
    rest = [t - s for s, t in zip(pv2, tv)]
    ax.plot(py2, pv2, color=p.NAVY, lw=2.6, label="Personal income tax alone")
    ax.fill_between(py2, 0, pv2, color=p.NAVY, alpha=0.10)
    ax.plot(ty, rest, color=p.TEAL, lw=2.6, label="All other revenue")
    ax.fill_between(ty, 0, rest, color=p.TEAL, alpha=0.10)
    ax.legend(loc="lower left", fontsize=8.6)
    ax.text(2006.3, 9.6, "one tax carries about half of federal revenue",
            fontsize=8.2, color=p.MUTED, style="italic")
    ax.set_ylim(0, 11)

    for a in ig.axes_flat:
        ig.style_axis(a)
        a.set_xlim(W0 - 0.6, 2024.6)


def plate_markets(ctx, ig) -> None:
    p = ctx.p

    ax = ig.next_panel("Target for the overnight rate (%)")
    ey, ev = _yr(ctx, "markets/rates.csv", "target_rate_eoy")
    ay, av = _yr(ctx, "markets/rates.csv", "target_rate_avg")
    ctx.line(ax, ay, av, p.FAINT, lw=1.8,
             label="annual average")
    ctx.line(ax, ey, ev, p.NAVY, label="year-end target")
    ctx.endlabel(ax, ey, ev, p.NAVY, lambda v: f"{v:.2f}%", dy=-18)
    ax.legend(loc="upper left", fontsize=8.6)
    ig.add_recessions(ax, inside=True)
    ax.set_yticks(range(0, 6))
    ax.annotate("4.25% to 0.25% in sixteen months", xy=(2009, 0.25),
                xytext=(2009.6, 2.2), fontsize=8.2, color=p.MUTED,
                style="italic",
                arrowprops=dict(arrowstyle="-", color=p.FAINT, lw=0.8))
    ig.add_event(ax, 2022.2, "the fastest hikes in decades", dy=0.28)
    ax.set_ylim(-0.4, 5.6)

    ax = ig.next_panel("Government of Canada benchmark yields "
                       "(%, annual average)")
    y2, v2 = _yr(ctx, "markets/rates.csv", "yield_2y_avg")
    y10, v10 = _yr(ctx, "markets/rates.csv", "yield_10y_avg")
    ctx.line(ax, y2, v2, p.BLUE, label="2-year")
    ctx.line(ax, y10, v10, p.NAVY, label="10-year")
    ax.legend(loc="upper right", fontsize=8.6)
    ig.add_recessions(ax, label=False)
    ax.annotate("the curve inverted through the hikes", xy=(2023, 4.27),
                xytext=(2015.4, 4.6), fontsize=8.2, color=p.MUTED,
                style="italic",
                arrowprops=dict(arrowstyle="-", color=p.FAINT, lw=0.8))
    ax.set_ylim(0, 5.2)
    ax.set_yticks(range(0, 6))

    ax = ig.next_panel("CAD per USD, annual average — rising = a weaker "
                       "Canadian dollar")
    ny, nv = _yr(ctx, "markets/usdcad.csv", "usd_cad_noon_avg")
    dy, dv = _yr(ctx, "markets/usdcad.csv", "usd_cad_daily_avg")
    ctx.line(ax, ny, nv, p.NAVY, dashed_partial=False,
             label="USD noon rate (retired March 2017)")
    ctx.line(ax, dy, dv, p.RED, label="the single daily rate (from 2017)")
    ctx.endlabel(ax, dy, dv, p.RED, lambda v: f"{v:.2f}", dy=10)
    ax.legend(loc="center left", fontsize=8.4)
    ig.add_event(ax, 2017.2, "the noon rate is retired", dy=0.97)
    ax.text(2006.0, 1.43, "2006–07: no full-year average exists —\n"
            "the StatCan annual table is pending",
            fontsize=7.8, color=p.FAINT, style="italic", va="top")
    ax.text(0.5, -0.125, "two series, computed differently, never spliced; "
            "2007 and 2017 are part-years and are left blank",
            transform=ax.transAxes, ha="center", fontsize=7.6,
            color=p.FAINT, style="italic")
    ax.set_ylim(0.95, 1.5)

    ax = ig.next_panel("S&P/TSX composite — annual close")
    ctx.pending(ax)
    ax.text(0.5, 0.36, "no official publisher; a redistributor feed is "
            "pending", transform=ax.transAxes, ha="center", fontsize=8.2,
            color=p.FAINT, style="italic")

    for a in ig.axes_flat:
        ig.style_axis(a)


def plate_world(ctx, ig) -> None:
    p = ctx.p

    ax = ig.next_panel("General-government debt, two measures (% of GDP)")
    gy, gv = _yr(ctx, "international/g7_gross_debt.csv", "canada", W0)
    ny, nv = _yr(ctx, "international/g7_net_debt.csv", "canada", W0)
    ay, av = _yr(ctx, "international/g7_gross_debt.csv", "g7_average", W0)
    ctx.line(ax, gy, gv, p.RED, label="Canada, gross")
    ctx.line(ax, ny, nv, p.NAVY, label="Canada, net of CPP/QPP assets")
    ctx.line(ax, ay, av, p.FAINT, lw=1.8, dashed_partial=False,
             label="G7 average, gross")
    ctx.endlabel(ax, gy, gv, p.RED, lambda v: f"{v:.1f}%", dy=8)
    ctx.endlabel(ax, ny, nv, p.NAVY, lambda v: f"{v:.1f}%", dy=-16)
    ax.legend(loc="upper left", fontsize=8.4)
    ax.text(2006.2, 60, "the net figure is low because the pension plans’\n"
            "assets are netted off — most of the G7 does not hold\n"
            "them in that form. Both measures are drawn, never net alone.",
            fontsize=7.8, color=p.MUTED, style="italic", va="top")
    ax.set_ylim(0, 150)

    ax = ig.next_panel("General-government balance (% of GDP, calendar years)")
    cy, cv = _yr(ctx, "international/g7_balance.csv", "canada", W0)
    gy2, gv2 = _yr(ctx, "international/g7_balance.csv", "g7_average", W0)
    ax.axhline(0, color=p.MUTED, lw=1.0)
    ctx.line(ax, gy2, gv2, p.FAINT, lw=1.8, dashed_partial=False,
             label="G7 average")
    ctx.line(ax, cy, cv, p.BLUE, label="Canada")
    worst = min(zip(cy, cv), key=lambda t: t[1])
    ax.annotate(f"{worst[1]:.1f}%", xy=worst, xytext=(2014.6, -11.4),
                fontsize=9, fontweight="bold", color=p.BLUE,
                arrowprops=dict(arrowstyle="-", color=p.FAINT, lw=0.8))
    ax.legend(loc="lower left", fontsize=8.6)
    ig.add_recessions(ax, label=False)
    ax.text(2013.5, -13.3, "all levels of government plus the CPP/QPP;\n"
            "calendar years — not comparable with the fiscal plates",
            fontsize=7.8, color=p.FAINT, style="italic", va="bottom")
    ax.set_ylim(-13.5, 3.5)

    ax = ig.next_panel("Human Development Index (UNDP)")
    hy, hv = _yr(ctx, "international/hdi.csv", "hdi")
    ctx.line(ax, hy, hv, p.GREEN_D, marker="o", ms=4.6,
             split_year=max(hy) if hy else None)
    ctx.endlabel(ax, hy, hv, p.GREEN_D, lambda v: f"{v:.3f}", dy=10)
    ax.axhline(0.9, color=p.FAINT, lw=0.9, ls=":")
    ax.text(2026.4, 0.9015, "0.900 = very high development", fontsize=8.0,
            color=p.MUTED, style="italic", ha="right", va="bottom")
    ig.add_event(ax, 2020.1, "pandemic dip", dy=0.30)
    ax.text(0.5, -0.125, "one vintage throughout — the HDR recomputes the "
            "whole back-series at each methodology change",
            transform=ax.transAxes, ha="center", fontsize=7.6,
            color=p.FAINT, style="italic")
    ax.set_ylim(0.88, 0.95)

    ax = ig.next_panel("Official reserves (US$ billion, year-end)")
    ry, rv = _yr(ctx, "international/reserves.csv", "reserves_usd")
    rv = [v / 1e9 for v in rv]
    ctx.line(ax, ry, rv, p.GREEN_D)
    ax.fill_between(ry, 0, rv, color=p.GREEN_D, alpha=0.08)
    ctx.endlabel(ax, ry, rv, p.GREEN_D, lambda v: f"US$ {v:,.0f}bn", dy=10)
    ax.text(2006.3, 118, "modest for a G7 economy — the dollar floats,\n"
            "so there is no peg to defend", fontsize=8.2, color=p.MUTED,
            style="italic", va="top")
    ax.set_ylim(0, 140)

    for a in ig.axes_flat:
        ig.style_axis(a)


def plate_migration(ctx, ig) -> None:
    p = ctx.p

    ax = ig.next_panel("Permanent residents admitted per year")
    ay, av = _yr(ctx, "migration/pr_admissions.csv", "admissions")
    ctx.bars(ax, ay, av, lambda v: p.RED)
    peak = max(((y, v) for y, v in zip(ay, av) if y <= ctx.LAST_FULL_YEAR),
               key=lambda t: t[1])
    ax.annotate(f"{peak[1]:,.0f}", peak, textcoords="offset points",
                xytext=(0, 6), ha="center", fontsize=9, fontweight="bold",
                color=p.RED)
    ax.annotate("the reversal: the 2025 levels plan\n"
                "cut admissions after the 2024 peak", xy=(2025, 390625),
                xytext=(2013.8, 460000), fontsize=8.2, color=p.MUTED,
                style="italic",
                arrowprops=dict(arrowstyle="-", color=p.FAINT, lw=0.8))
    ax.text(2006.2, 380000, "IRCC’s open data begins in 2015:\n"
            "2006–14 are not in this series\n(and the cells are rounded "
            "to fives)", fontsize=8.0, color=p.FAINT, style="italic",
            va="top")
    ig.mark_partial(ax, 2026, "2026: partial")
    ax.set_ylim(0, 560000)

    ax = ig.next_panel("Top ten countries of citizenship "
                       "(thousands admitted per year)")
    ORIG = [("india", "India"), ("philippines", "Philippines"),
            ("china,_people's_republic_of", "China"), ("nigeria", "Nigeria"),
            ("syria", "Syria"), ("pakistan", "Pakistan"),
            ("united_states_of_america", "United States"), ("france", "France"),
            ("iran", "Iran"), ("afghanistan", "Afghanistan")]
    series = [_yr(ctx, "migration/pr_by_origin.csv", c) for c, _ in ORIG]
    yrs = [y for y in series[0][0] if y <= ctx.LAST_FULL_YEAR]
    stack = [[v / 1000 for y, v in zip(sy, sv) if y <= ctx.LAST_FULL_YEAR]
             for sy, sv in series]
    ax.stackplot(yrs, *stack, labels=[l for _, l in ORIG],
                 colors=[p.cycle(i) for i in range(len(ORIG))],
                 alpha=0.92, lw=0)
    ax.legend(loc="upper left", fontsize=7.4, ncol=2)
    top = max(sum(vals) for vals in zip(*stack))
    ax.text(0.5, -0.125, "ranked once over the whole file; the rest of the "
            "world is not drawn", transform=ax.transAxes, ha="center",
            fontsize=7.6, color=p.FAINT, style="italic")
    ax.set_ylim(0, top * 1.42)

    ax = ig.next_panel("Study permits signed per year — a flow, "
                       "not the stock (thousands)")
    sy, sv = _yr(ctx, "migration/study_permits.csv", "permit_holders")
    ctx.bars(ax, sy, [v / 1000 for v in sv], lambda v: p.TEAL)
    peak = max(((y, v / 1000) for y, v in zip(sy, sv)
                if y <= ctx.LAST_FULL_YEAR), key=lambda t: t[1])
    ax.annotate(f"{peak[1]:,.0f}k", peak, textcoords="offset points",
                xytext=(0, 6), ha="center", fontsize=9, fontweight="bold",
                color=p.TEAL)
    ig.mark_partial(ax, 2026, "2026: partial")
    ax.text(2006.2, 640, "permits signed in the period — a permit runs\n"
            "for years, so the stock of students present is\n"
            "several times larger. That stock is StatCan’s\n"
            "non-permanent-resident estimate, pending.",
            fontsize=7.8, color=p.FAINT, style="italic", va="top")
    ax.set_ylim(0, 800)

    ax = ig.next_panel("Population (millions)")
    py, pv = _yr(ctx, "international/population.csv", "population")
    pv = [v / 1e6 for v in pv]
    ctx.line(ax, py, pv, p.BLUE)
    ax.fill_between(py, 30, pv, color=p.BLUE, alpha=0.07)
    ctx.endlabel(ax, py, pv, p.BLUE, lambda v: f"{v:.1f}M", dy=10)
    ax.annotate("+3% a year in 2023–24, unmatched in the G7 —\n"
                "and most of it non-permanent residents", xy=(2023.5, 40.7),
                xytext=(2006.4, 40.4), fontsize=8.2, color=p.MUTED,
                style="italic",
                arrowprops=dict(arrowstyle="-", color=p.FAINT, lw=0.8))
    ax.text(0.5, -0.125, "World Bank series; Statistics Canada’s quarterly "
            "estimate, the one that separates\nnon-permanent residents, is "
            "pending while its platform is down",
            transform=ax.transAxes, ha="center", va="top", fontsize=7.6,
            color=p.FAINT, style="italic")
    ax.set_ylim(30, 44)

    for a in ig.axes_flat:
        ig.style_axis(a)


# The plates, in the order the page lists them. The numbers keep the spine
# positions: when Statistics Canada returns, the missing chapters slot into
# theirs without renumbering anything here.
PLATES = (
    dict(id="02", slug="fiscal", builder=plate_fiscal,
         title="The Federal Books — Revenue, Deficits and Debt, 2006–2026",
         subtitle="Ottawa’s own accounts, by fiscal year: April to March, "
                  "labelled by the year the year starts in.",
         source="Source: Department of Finance Canada — Fiscal Reference "
                "Tables, November 2025",
         alt="Four panels on federal public finances, fiscal years 2006-07 "
             "to 2024-25. Revenues run near 16% of GDP while expenses spike "
             "to 29% in 2020-21; the budgetary balance reaches −14.8% of "
             "GDP that year, the largest federal deficit in peacetime; "
             "public debt charges return to 1.7% of GDP by 2024; and the "
             "accumulated deficit reaches C$1.27 trillion against C$1.39 "
             "trillion of net debt since 1966."),
    dict(id="03", slug="spending", builder=plate_spending,
         title="Where Ottawa Spends It — and Where It Comes From, 2006–2026",
         subtitle="Federal expenses by category and revenues by source, "
                  "per cent of GDP, fiscal years.",
         source="Source: Department of Finance Canada — Fiscal Reference "
                "Tables, November 2025",
         alt="Four panels on the composition of federal spending and "
             "revenue. Transfers to persons, transfers to provinces and "
             "direct program expenses each run near 4-8% of GDP with a "
             "pandemic spike in 2020-21; personal income tax at about 7-8% "
             "of GDP carries roughly half of all federal revenue."),
    dict(id="05", slug="markets", builder=plate_markets,
         title="Money & Markets — the Policy Rate, Bond Yields and the Dollar",
         subtitle="The Bank of Canada’s target rate, Government of Canada "
                  "benchmark yields, and the two exchange-rate series that "
                  "must never be spliced.",
         source="Source: Bank of Canada — Valet API",
         alt="Four panels on Canadian money markets. The overnight target "
             "falls from 4.25% in 2007 to 0.25% in 2009, sits at 1% for "
             "years, then rises to 5% by 2023 before easing to 2.25%; bond "
             "yields follow; the Canadian dollar weakens from near parity "
             "to about 1.40 per US dollar, with the noon-rate series "
             "retired in 2017 and never spliced into its successor; the "
             "TSX panel is pending a redistributor feed."),
    dict(id="07", slug="world", builder=plate_world,
         title="Canada in the World — Debt, Balance, Development and Reserves",
         subtitle="How the G7 reads Canada’s books — general government, "
                  "calendar years — plus the UNDP and World Bank comparables.",
         source="Sources: IMF via Fiscal Reference Tables 2025 · UNDP HDR "
                "2025 · World Bank WDI",
         alt="Four panels on Canada among the G7. Gross general-government "
             "debt is 111% of GDP in 2024, near the G7 average, while the "
             "net measure reads 12.5% because CPP/QPP assets are netted "
             "off; the general-government balance reaches −10.9% of GDP in "
             "2020; the Human Development Index stands at 0.939; official "
             "reserves reach US$126 billion."),
    dict(id="12", slug="migration", builder=plate_migration,
         title="Migration — Who Arrives, and How the Policy Reversed",
         subtitle="IRCC’s open data begins in 2015; the population series "
                  "is the World Bank’s, pending Statistics Canada.",
         source="Sources: IRCC open data · World Bank WDI",
         alt="Four panels on Canadian migration. Permanent-resident "
             "admissions run from 270,000 in 2015 to a 480,955 peak in "
             "2024, then are cut to about 390,000 in 2025; India and the "
             "Philippines are the largest countries of citizenship; study "
             "permits signed peak at 700,000 in 2023; the population grows "
             "by about 3% a year in 2023-24, the fastest in the G7."),
)
