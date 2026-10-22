"""The argentina plates.

Each function draws one plate from this country's committed CSVs and saves it
through the context, which resolves every path under countries/argentina/ and
knows this country's palette, year span and last complete year. Ported from
the standalone argentina-reports scripts/charts.py; the drawing is unchanged.
"""
from __future__ import annotations

from matplotlib.ticker import FuncFormatter

from core.sideload import sibling

# Argentina reads its CSVs through its own loader, which lives beside the
# data it reads and so cannot address another country's files.
ds = sibling(__file__, "datasets")
events = sibling(__file__, "events")


def _line(ctx, ax, series, color=None, label="", lw=2.2, marker="o",
         ms=3.4, ls="-", zorder=3, alpha=1.0):
    # Gapped by default: a year with no reading breaks the line rather than
    # being bridged. See datasets.xy_gapped.
    color = color or ctx.p.CELESTE
    years, values = ds.xy_gapped(series)
    ax.plot(years, values, color=color, lw=lw, marker=marker, ms=ms,
            label=label, ls=ls, zorder=zorder, alpha=alpha)
    return years, values

def _bars(ctx, ax, series, color=None, label="", width=0.72, alpha=1.0):
    color = color or ctx.p.CELESTE
    years, values = ds.xy(series)
    ax.bar(years, values, width=width, color=color, label=label,
           alpha=alpha, zorder=2)
    return years, values

def _signed_bars(ctx, ax, series, width=0.72):
    years, values = ds.xy(series)
    colors = [ctx.p.GREEN if v >= 0 else ctx.p.RED for v in values]
    ax.bar(years, values, width=width, color=colors, zorder=2)
    ax.axhline(0, color=ctx.p.INK, lw=0.9, zorder=3)
    return years, values

def _end_label(ctx, ax, series, text=None, color=None, dx=0.25,
               fmt="{:,.1f}"):
    """Name the last point, so a line does not need a legend to be read."""
    color = color or ctx.p.INK
    if not series:
        return
    year = max(series)
    value = series[year]
    ax.annotate(text if text is not None else fmt.format(value),
                (year + dx, value), fontsize=9, fontweight="bold",
                color=color, va="center", ha="left", clip_on=False, zorder=7)

def _pct_axis(ax, decimals=0):
    ax.yaxis.set_major_formatter(
        FuncFormatter(lambda v, _: f"{v:,.{decimals}f}%"))

def _indec_gap(ctx, ax, label="INDEC intervened — official figures withdrawn"):
    """Band the decade the state itself disavowed. Used wherever a series
    would otherwise be drawn straight through it."""
    start, end = events.INDEC_GAP
    ax.axvspan(start, end, color=ctx.p.BAND, zorder=0)
    ax.text((start + end) / 2, 0.5, label, transform=ax.get_xaxis_transform(),
            ha="center", va="center", fontsize=8.2, color=ctx.p.MUTED,
            style="italic", rotation=0, zorder=1,
            bbox=dict(boxstyle="round,pad=0.35", facecolor=ctx.p.PAPER,
                      edgecolor=ctx.p.SPINE, linewidth=0.6))

def _note(ctx, ax, x, y, text, color=None, ha="left", fontsize=8.2,
          width=None):
    """A caveat placed **where the thing it explains is**, in axis
    coordinates. Captions in the far corner of a figure are not read as
    belonging to the line they describe."""
    color = color or ctx.p.MUTED
    ax.text(x, y, text, transform=ax.transAxes, ha=ha, va="top",
            fontsize=fontsize, color=color, style="italic", zorder=8,
            bbox=dict(boxstyle="round,pad=0.4", facecolor=ctx.p.PAPER,
                      edgecolor=ctx.p.SPINE, linewidth=0.6, alpha=0.95),
            wrap=width is not None)

def _headroom(ax, top: float = 0.18, bottom: float = 0.0) -> None:
    """Grow the y range so a peak label has somewhere to sit.

    A value annotation drawn at the highest point of a panel lands on the
    panel title unless the axis makes room for it. matplotlib will not do
    this: its autoscaling only knows about the data.
    """
    lo, hi = ax.get_ylim()
    span = hi - lo
    ax.set_ylim(lo - span * bottom, hi + span * top)

def _legend(ctx, ax, loc="upper left", ncol=1):
    ax.legend(loc=loc, ncol=ncol, frameon=False, fontsize=9.2,
              labelcolor=ctx.p.MUTED, handlelength=1.6)

def plate_output(ctx, fig) -> None:
    gdp = ds.load("macro/gdp.csv")

    ax = fig.next_panel("Gross domestic product, US$ billion")
    _bars(ctx, ax, gdp["usd_bn"], color=ctx.p.CELESTE)
    fig.style_axis(ax)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    _headroom(ax, top=0.30)
    peak = max(gdp["usd_bn"], key=lambda y: gdp["usd_bn"][y])
    ctx.annotate_value(ax, peak, gdp["usd_bn"][peak],
                     f"peak {gdp['usd_bn'][peak]:,.0f}", color=ctx.p.NAVY)
    _end_label(ctx, ax, gdp["usd_bn"], fmt="{:,.0f}", color=ctx.p.CELESTE_D)
    _note(ctx, ax, 0.02, 0.96,
         "Dollar GDP moves with the exchange rate as well as with output.\n"
         "The real-growth panel below is the one to read for activity.")

    ax = fig.next_panel("Real GDP growth, % per year")
    years, values = _signed_bars(ctx, ax, gdp["real_growth"])
    fig.style_axis(ax)
    _pct_axis(ax)
    _headroom(ax, top=0.10, bottom=0.22)
    for year in (2009, 2020):
        if year in gdp["real_growth"]:
            ctx.annotate_value(ax, year, gdp["real_growth"][year],
                             f"{gdp['real_growth'][year]:.1f}%",
                             color=ctx.p.RED, offset=(0, -22))
    mean = sum(values) / len(values)
    ax.axhline(mean, color=ctx.p.MUTED, lw=1.0, ls=(0, (4, 3)), zorder=4)
    # 2026 has no growth bar yet, so the mean label goes in that slot.
    ax.text(ds.LAST_YEAR, mean, f"mean\n{mean:.1f}%", fontsize=7.8,
            color=ctx.p.MUTED, va="bottom", ha="center", linespacing=1.1)

    ax = fig.next_panel("GDP per capita, US$")
    _line(ctx, ax, gdp["gdp_per_capita_usd"], color=ctx.p.NAVY)
    fig.style_axis(ax)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    _headroom(ax)
    _end_label(ctx, ax, gdp["gdp_per_capita_usd"], fmt="{:,.0f}", color=ctx.p.NAVY)
    peak = max(gdp["gdp_per_capita_usd"], key=gdp["gdp_per_capita_usd"].get)
    ctx.annotate_value(ax, peak, gdp["gdp_per_capita_usd"][peak],
                     f"{gdp['gdp_per_capita_usd'][peak]:,.0f} in {peak}",
                     color=ctx.p.NAVY)

    ax = fig.next_panel("Real output, 2006 = 100")
    growth = gdp["real_growth"]
    index, level = {}, 100.0
    for year in sorted(growth):
        level *= 1 + growth[year] / 100
        index[year] = level
    index[ds.FIRST_YEAR] = 100.0
    _line(ctx, ax, index, color=ctx.p.CELESTE_D)
    ax.axhline(100, color=ctx.p.MUTED, lw=0.9, ls=(0, (4, 3)))
    fig.style_axis(ax)
    _end_label(ctx, ax, index, fmt="{:,.0f}", color=ctx.p.CELESTE_D)
    _headroom(ax, top=0.35)
    _note(ctx, ax, 0.02, 0.99,
         "Twenty years of growth and recession that\n"
         "very nearly cancel: the economy ends the\n"
         "window close to where the index starts.")

def plate_prices(ctx, fig) -> None:
    ipc = ds.load("macro/ipc.csv")
    fx = ds.load("macro/dollar.csv")
    par = ds.load("markets/parallel_fx.csv")
    res = ds.load("macro/reserves.csv")

    ax = fig.next_panel("Consumer price inflation, % per year")
    _indec_gap(ctx, ax, "no usable official index")
    _bars(ctx, ax, ipc["official"], color=ctx.p.CELESTE, label="INDEC, national index")
    _bars(ctx, ax, ipc["alternative"], color=ctx.p.ASTERISK,
         label="IPC San Luis (official, provincial)")
    fig.style_axis(ax)
    _pct_axis(ax)
    _headroom(ax, top=0.22)
    _legend(ctx, ax)
    peak = max(ipc["official"], key=ipc["official"].get)
    ctx.annotate_value(ax, peak, ipc["official"][peak],
                     f"{ipc['official'][peak]:.0f}%", color=ctx.p.CELESTE_D)
    _end_label(ctx, ax, ipc["official"], fmt="{:.0f}%", color=ctx.p.CELESTE_D)

    ax = fig.next_panel("Pesos per US dollar, log scale")
    _line(ctx, ax, fx["official_eop"], color=ctx.p.NAVY, label="official rate")
    _line(ctx, ax, par["blue"], color=ctx.p.ASTERISK, label="parallel (blue)", ls=(0, (5, 2)))
    ax.set_yscale("log")
    fig.style_axis(ax)
    ax.set_ylim(2, max(par["blue"].values()) * 6)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    _legend(ctx, ax, loc="lower right")
    _end_label(ctx, ax, fx["official_eop"], fmt="{:,.0f}", color=ctx.p.NAVY)
    _note(ctx, ax, 0.02, 0.97,
         "Under the two cepos the official rate was a price\n"
         "at which most people could not buy. The gap is the\n"
         "story, so both lines are drawn.")

    ax = fig.next_panel("Exchange-rate gap, parallel over official, %")
    gap = {y: (par["blue"][y] / fx["official_eop"][y] - 1) * 100
           for y in par["blue"] if y in fx["official_eop"]}
    _bars(ctx, ax, gap, color=ctx.p.SUN)
    fig.style_axis(ax)
    _pct_axis(ax)
    _headroom(ax, top=0.20)
    # The band labels go inside the panel, near its top: above the axes
    # they collide with the panel title, and at the foot they sit on the
    # bars they are meant to frame.
    for start, end, label in ((2011.9, 2015.95, "cepo I"),
                              (2019.7, 2025.3, "cepo II")):
        fig.add_band(ax, start, end)
        ax.text((start + end) / 2, 0.955, label, ha="center", va="top",
                transform=ax.get_xaxis_transform(), fontsize=8.4,
                color=ctx.p.MUTED, style="italic", zorder=4)
    peak = max(gap, key=gap.get)
    ctx.annotate_value(ax, peak, gap[peak], f"{gap[peak]:.0f}%", color=ctx.p.NAVY)

    ax = fig.next_panel("Central bank reserves, US$ billion, year end")
    _bars(ctx, ax, res["eop_usbi"], color=ctx.p.TEAL)
    fig.style_axis(ax)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    trough = min(res["eop_usbi"], key=res["eop_usbi"].get)
    ctx.annotate_value(ax, trough, res["eop_usbi"][trough],
                     f"{res['eop_usbi'][trough]:.1f}", color=ctx.p.RED,
                     offset=(0, 6))
    _end_label(ctx, ax, res["eop_usbi"], fmt="{:,.1f}", color=ctx.p.TEAL)

def plate_living(ctx, fig) -> None:
    unemp = ds.load("macro/unemployment.csv")
    wage = ds.load("macro/minimum_wage.csv")
    pov = ds.load("social/poverty.csv")
    gini = ds.load("social/gini.csv")

    ax = fig.next_panel("Unemployment rate, %")
    _line(ctx, ax, unemp["value"], color=ctx.p.CELESTE)
    fig.style_axis(ax)
    _pct_axis(ax, 0)
    _headroom(ax)
    _end_label(ctx, ax, unemp["value"], fmt="{:.1f}%", color=ctx.p.CELESTE_D)
    peak = max(unemp["value"], key=unemp["value"].get)
    ctx.annotate_value(ax, peak, unemp["value"][peak],
                     f"{unemp['value'][peak]:.1f}%", color=ctx.p.NAVY)

    ax = fig.next_panel("Minimum wage, US$ per month at the official rate")
    _bars(ctx, ax, wage["usd_official"], color=ctx.p.CELESTE_D)
    fig.style_axis(ax)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    _headroom(ax, top=0.48)
    peak = max(wage["usd_official"], key=wage["usd_official"].get)
    ctx.annotate_value(ax, peak, wage["usd_official"][peak],
                     f"{wage['usd_official'][peak]:,.0f}", color=ctx.p.NAVY)
    _end_label(ctx, ax, wage["usd_official"], fmt="{:,.0f}", color=ctx.p.CELESTE_D)
    _note(ctx, ax, 0.02, 0.97,
         "In pesos the minimum wage rises every year. Prices\n"
         "rose about 1,200-fold over the same window, so the\n"
         "peso figure is not a series; the dollar one is.")

    ax = fig.next_panel("People below the poverty line, % — each half year")
    _indec_gap(ctx, ax, "withdrawn by the 2016 statistical emergency")
    _line(ctx, ax, pov["s1"], color=ctx.p.CELESTE, label="first half")
    _line(ctx, ax, pov["s2"], color=ctx.p.NAVY, label="second half", ls=(0, (5, 2)))
    fig.style_axis(ax)
    _pct_axis(ax)
    _headroom(ax, top=0.16)
    _legend(ctx, ax, loc="lower left", ncol=2)
    if 2024 in pov["s1"]:
        ctx.annotate_value(ax, 2024, pov["s1"][2024],
                         f"{pov['s1'][2024]:.1f}%", color=ctx.p.RED,
                         offset=(-6, 6), ha="right")
        _note(ctx, ax, 0.02, 0.99,
             "52.9% is the FIRST half of 2024 — the half after the\n"
             "December 2023 devaluation. The second half was 38.1%.\n"
             "The source dates this series at the end of its half year.")

    ax = fig.next_panel("Gini coefficient of per-capita family income")
    _indec_gap(ctx, ax, "withdrawn")
    _line(ctx, ax, gini["indec"], color=ctx.p.PURPLE)
    fig.style_axis(ax)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.3f}"))
    _end_label(ctx, ax, gini["indec"], fmt="{:.3f}", color=ctx.p.PURPLE)
    _headroom(ax, top=0.40, bottom=0.10)
    _note(ctx, ax, 0.98, 0.99,
         "Lower is more equal. The annual average hides a\n"
         "quarterly spike to 0.467 in the first quarter of 2024.",
         ha="right")

def plate_state(ctx, fig) -> None:
    prim = ds.load("fiscal/primary_result.csv")
    tax = ds.load("fiscal/tax_revenue.csv")
    spend = ds.load("fiscal/spending_by_function.csv")

    ax = fig.next_panel("Primary balance of the national public sector, % of GDP")
    # Three incompatible methodologies, drawn as three segments. Joining
    # them into one line would imply a continuity the source denies.
    palette = {"m1993": ctx.p.FAINT, "m2007": ctx.p.CELESTE, "m2017": ctx.p.NAVY}
    names = {"m1993": "1993 methodology", "m2007": "2007 methodology",
             "m2017": "2015 methodology"}
    for key, color in palette.items():
        if prim.get(key):
            _line(ctx, ax, prim[key], color=color, label=names[key], lw=2.4)
    ax.axhline(0, color=ctx.p.INK, lw=0.9)
    fig.style_axis(ax)
    _pct_axis(ax, 1)
    _legend(ctx, ax, loc="lower left")
    if 2024 in prim["m2017"]:
        ctx.annotate_value(ax, 2024, prim["m2017"][2024],
                         f"+{prim['m2017'][2024]:.2f}%", color=ctx.p.GREEN)
    _headroom(ax, top=0.60)
    _note(ctx, ax, 0.98, 0.99,
         "The three segments are not one series. The treatment of\n"
         "central-bank transfers and pension income changes at each\n"
         "break by more than the deficit moves in a normal year.",
         ha="right")

    ax = fig.next_panel("Tax revenue, % of GDP")
    _bars(ctx, ax, tax["total_pct_gdp"], color=ctx.p.CELESTE)
    _line(ctx, ax, tax["export_duties_pct_gdp"], color=ctx.p.SUN,
         label="of which export duties", lw=2.0)
    _line(ctx, ax, tax["ganancias_pct_gdp"], color=ctx.p.RED,
         label="of which income tax", lw=2.0)
    fig.style_axis(ax)
    _pct_axis(ax)
    _headroom(ax, top=0.45)
    _legend(ctx, ax, loc="upper right")
    _note(ctx, ax, 0.02, 0.99,
         "The two lines are components of the bars, not separate totals.")

    ax = fig.next_panel("Primary spending by function, % of GDP")
    groups = [("prevision", "pensions", ctx.p.NAVY),
              ("salud_obras", "health insurance", ctx.p.TEAL),
              ("educacion_superior", "education", ctx.p.CELESTE),
              ("energia", "energy subsidies", ctx.p.SUN),
              ("asistencia", "social assistance", ctx.p.GREEN),
              ("transporte", "transport", ctx.p.PURPLE)]
    years = sorted(set.intersection(*(set(spend[k]) for k, _, _ in groups)))
    bottom = [0.0] * len(years)
    for key, label, color in groups:
        values = [spend[key][y] for y in years]
        ax.bar(years, values, bottom=bottom, width=0.78, color=color,
               label=label, zorder=2)
        bottom = [b + v for b, v in zip(bottom, values)]
    fig.style_axis(ax)
    _pct_axis(ax)
    _headroom(ax, top=0.62)
    _legend(ctx, ax, loc="upper left", ncol=3)
    _note(ctx, ax, 0.98, 0.74,
         "Consolidated spending series ends in 2023.", ha="right")

    ax = fig.next_panel("Pensions against debt interest, % of GDP")
    _line(ctx, ax, spend["prevision"], color=ctx.p.NAVY, label="pensions")
    _line(ctx, ax, spend["deuda"], color=ctx.p.RED, label="debt service")
    fig.style_axis(ax)
    _pct_axis(ax)
    _legend(ctx, ax)
    _end_label(ctx, ax, spend["prevision"], fmt="{:.1f}%", color=ctx.p.NAVY)
    _end_label(ctx, ax, spend["deuda"], fmt="{:.1f}%", color=ctx.p.RED)

def plate_trade(ctx, fig) -> None:
    trade = ds.load("trade/trade.csv")
    rubros = ds.load_long("trade/exports_rubros.csv", "rubro", "usbi")

    ax = fig.next_panel("Exports and imports, US$ billion")
    _line(ctx, ax, trade["exports"], color=ctx.p.GREEN, label="exports")
    _line(ctx, ax, trade["imports"], color=ctx.p.RED, label="imports")
    fig.style_axis(ax)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    _legend(ctx, ax)
    _end_label(ctx, ax, trade["exports"], fmt="{:,.0f}", color=ctx.p.GREEN)
    _end_label(ctx, ax, trade["imports"], fmt="{:,.0f}", color=ctx.p.RED)
    fig.mark_partial(ax, 2026, "2026: year to date")

    ax = fig.next_panel("Trade balance, US$ billion")
    _signed_bars(ctx, ax, trade["balance"])
    fig.style_axis(ax)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    _headroom(ax, top=0.18, bottom=0.26)
    best = max(trade["balance"], key=trade["balance"].get)
    worst = min(trade["balance"], key=trade["balance"].get)
    ctx.annotate_value(ax, best, trade["balance"][best],
                     f"{trade['balance'][best]:,.1f}", color=ctx.p.GREEN)
    ctx.annotate_value(ax, worst, trade["balance"][worst],
                     f"{trade['balance'][worst]:,.1f}", color=ctx.p.RED,
                     offset=(0, -20))

    ax = fig.next_panel("Exports by category, US$ billion")
    order = [("primarios", "primary products", ctx.p.GREEN),
             ("moa", "agricultural manufactures", ctx.p.TEAL),
             ("moi", "industrial manufactures", ctx.p.CELESTE),
             ("combustibles", "fuel and energy", ctx.p.SUN)]
    years = sorted(set.intersection(*(set(rubros[k]) for k, _, _ in order)))
    bottom = [0.0] * len(years)
    for key, label, color in order:
        values = [rubros[key][y] for y in years]
        ax.bar(years, values, bottom=bottom, width=0.78, color=color,
               label=label, zorder=2)
        bottom = [b + v for b, v in zip(bottom, values)]
    fig.style_axis(ax)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    _headroom(ax, top=0.58)
    _legend(ctx, ax, loc="upper left", ncol=2)
    _note(ctx, ax, 0.98, 0.74,
         "Industrial manufactures are the residual of the other\n"
         "three: the category's own series is served empty.",
         ha="right")

    ax = fig.next_panel("Fuel and energy, share of exports, %")
    total = {y: sum(rubros[k][y] for k, _, _ in order) for y in years}
    share = {y: rubros["combustibles"][y] / total[y] * 100 for y in years}
    _bars(ctx, ax, share, color=ctx.p.SUN)
    fig.style_axis(ax)
    _pct_axis(ax)
    _end_label(ctx, ax, share, fmt="{:.1f}%", color=ctx.p.NAVY)

def plate_credit(ctx, fig) -> None:
    credit = ds.load("macro/credit.csv")
    rates = ds.load("macro/rates.csv")
    quality = ds.load("macro/credit_quality.csv")

    ax = fig.next_panel("Credit to the private sector, % of GDP")
    _bars(ctx, ax, credit["private_pct_gdp"], color=ctx.p.CELESTE,
         label="all private credit")
    _bars(ctx, ax, credit["households_pct_gdp"], color=ctx.p.NAVY, width=0.42,
         label="of which households")
    fig.style_axis(ax)
    _pct_axis(ax)
    ax.set_ylim(0, max(credit["private_pct_gdp"].values()) * 1.75)
    _legend(ctx, ax, loc="upper right")
    _note(ctx, ax, 0.02, 0.98,
         "The narrow bars are a part of the wide ones, not a second total.\n"
         "Note the scale: Chile and Brazil lend 50-70% of GDP. Argentina's\n"
         "2024-25 credit boom is large in relative terms only.")
    _end_label(ctx, ax, credit["private_pct_gdp"], fmt="{:.1f}%", color=ctx.p.CELESTE_D)

    ax = fig.next_panel("Household borrowing by type, % of GDP")
    for key, label, color in (("cards", "credit cards", ctx.p.SUN),
                              ("personal", "personal loans", ctx.p.CELESTE),
                              ("mortgage", "mortgages", ctx.p.RED),
                              ("pledge", "pledge loans", ctx.p.TEAL)):
        _line(ctx, ax, credit[f"{key}_pct_gdp"], color=color, label=label, lw=2.0)
    fig.style_axis(ax)
    _pct_axis(ax, 1)
    ax.set_ylim(0, max(credit["cards_pct_gdp"].values()) * 1.35)
    _legend(ctx, ax, loc="upper right", ncol=2)
    _note(ctx, ax, 0.02, 0.99,
         "Mortgage lending did not shrink, it stopped:\n"
         "1.56% of GDP in 2008, 0.28% in 2024.")

    ax = fig.next_panel("Real interest rates, % per year")
    _line(ctx, ax, rates["deposit_30d_real"], color=ctx.p.GREEN,
         label="paid on a 30-day deposit")
    _line(ctx, ax, rates["personal_loan_real"], color=ctx.p.RED,
         label="charged on a personal loan")
    ax.axhline(0, color=ctx.p.INK, lw=0.9)
    fig.style_axis(ax)
    _pct_axis(ax)
    _legend(ctx, ax, loc="lower left")
    _note(ctx, ax, 0.02, 0.97,
         "Nominal rates say almost nothing here: 95.9% on a deposit in\n"
         "2023 was a 37% real loss. Saving was punished every year from\n"
         "2017 to 2024; from 2025 borrowing is punished instead.")

    ax = fig.next_panel("Non-performing loans, % of credit to the private sector")
    _bars(ctx, ax, quality["npl_private_pct"], color=ctx.p.RED)
    fig.style_axis(ax)
    _pct_axis(ax, 1)
    ax.set_ylim(0, max(quality["npl_private_pct"].values()) * 1.45)
    peak = max(quality["npl_private_pct"], key=quality["npl_private_pct"].get)
    ctx.annotate_value(ax, peak, quality["npl_private_pct"][peak],
                     f"{quality['npl_private_pct'][peak]:.2f}%", color=ctx.p.RED)
    _note(ctx, ax, 0.02, 0.97,
         "The credit expansion and this spike are the same\n"
         "event seen a year apart.")

def plate_markets(ctx, fig) -> None:
    merval = ds.load("markets/merval.csv")
    sp500 = ds.load("markets/sp500.csv")
    fx = ds.load("macro/dollar.csv")
    risk = ds.load("markets/country_risk.csv")

    merval_usd = {y: merval["close"][y] / fx["official_eop"][y]
                  for y in merval["close"] if y in fx["official_eop"]}

    ax = fig.next_panel("Merval in dollars against the S&P 500, 2006 = 100")
    for series, color, label in ((merval_usd, ctx.p.CELESTE, "Merval, in US$"),
                                 (sp500["close"], ctx.p.MUTED, "S&P 500")):
        base = series[ds.FIRST_YEAR]
        _line(ctx, ax, {y: v / base * 100 for y, v in series.items()},
             color=color, label=label)
    ax.set_yscale("log")
    ax.axhline(100, color=ctx.p.MUTED, lw=0.8, ls=(0, (4, 3)))
    fig.style_axis(ax)
    ax.set_ylim(25, 1200)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    _legend(ctx, ax, loc="upper left")
    _note(ctx, ax, 0.98, 0.22,
         "Neither index is an official statistic: BYMA publishes no open\n"
         "history for its own index, so both closes come from a vendor.",
         ha="right")

    ax = fig.next_panel("Country risk, EMBI+ Argentina, basis points")
    _bars(ctx, ax, risk["avg_bp"], color=ctx.p.ASTERISK, label="annual average")
    _line(ctx, ax, risk["eop_bp"], color=ctx.p.NAVY, label="year end", lw=2.0)
    fig.style_axis(ax)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    _legend(ctx, ax)
    _end_label(ctx, ax, risk["eop_bp"], fmt="{:,.0f}", color=ctx.p.NAVY)

    ax = fig.next_panel("Merval in dollars, index points")
    _line(ctx, ax, merval_usd, color=ctx.p.CELESTE_D)
    fig.style_axis(ax)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    _headroom(ax, top=0.20)
    peak = max(merval_usd, key=merval_usd.get)
    ctx.annotate_value(ax, peak, merval_usd[peak], f"{merval_usd[peak]:,.0f}",
                     color=ctx.p.NAVY)
    _end_label(ctx, ax, merval_usd, fmt="{:,.0f}", color=ctx.p.CELESTE_D)

    ax = fig.next_panel("Reserves against country risk")
    res = ds.load("macro/reserves.csv")["eop_usbi"]
    _line(ctx, ax, res, color=ctx.p.TEAL, label="reserves, US$ bn (left)")
    fig.style_axis(ax)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    twin = ax.twinx()
    years, values = ds.xy(risk["eop_bp"])
    twin.plot(years, values, color=ctx.p.RED, lw=2.0, marker="o", ms=3.4,
              label="country risk, bp (right)")
    twin.spines[["top", "left", "right"]].set_visible(False)
    twin.tick_params(length=0, colors=ctx.p.MUTED)
    twin.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    twin.grid(False)
    handles = ax.get_legend_handles_labels()[0] + \
        twin.get_legend_handles_labels()[0]
    labels = ax.get_legend_handles_labels()[1] + \
        twin.get_legend_handles_labels()[1]
    _headroom(ax, top=0.30)
    ax.legend(handles, labels, loc="upper center", frameon=False,
              fontsize=9.2, labelcolor=ctx.p.MUTED)

def plate_people(ctx, fig) -> None:
    vitals = ds.load("social/vitals.csv")
    causes = ds.load("social/causes.csv")

    ax = fig.next_panel("Births and deaths registered, thousands")
    births = {y: v / 1000 for y, v in vitals["births"].items()}
    deaths = {y: v / 1000 for y, v in vitals["deaths"].items()}
    _line(ctx, ax, births, color=ctx.p.CELESTE, label="births")
    _line(ctx, ax, deaths, color=ctx.p.NAVY, label="deaths")
    fig.style_axis(ax)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    _headroom(ax, top=0.30, bottom=0.30)
    _legend(ctx, ax, loc="lower left", ncol=2)
    peak = max(births, key=births.get)
    ctx.annotate_value(ax, peak, births[peak], f"{births[peak]:,.0f}k",
                     color=ctx.p.CELESTE_D, offset=(0, 7))
    _end_label(ctx, ax, births, fmt="{:,.0f}k", color=ctx.p.CELESTE_D)
    _end_label(ctx, ax, deaths, fmt="{:,.0f}k", color=ctx.p.NAVY)
    _note(ctx, ax, 0.98, 0.99,
         "Births fell 46.8% in ten years, from 777,012 in 2014 to\n"
         "413,135 in 2024. The two lines are converging, not crossed.",
         ha="right")

    ax = fig.next_panel("Natural increase, births minus deaths, thousands")
    growth = {y: v / 1000 for y, v in vitals["natural_growth"].items()}
    _bars(ctx, ax, growth, color=ctx.p.GREEN)
    fig.style_axis(ax)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    last = max(growth)
    ctx.annotate_value(ax, last, growth[last], f"{growth[last]:,.0f}k",
                     color=ctx.p.NAVY)
    _headroom(ax, top=0.30)
    _note(ctx, ax, 0.02, 0.99,
         "451,000 more births than deaths in 2014.\n"
         "36,700 in 2024.")

    ax = fig.next_panel("Deaths from COVID-19 and from pneumonia, thousands")
    covid = {y: v / 1000 for y, v in causes["covid"].items() if v}
    pneumonia = {y: v / 1000 for y, v in causes["pneumonia"].items()}
    _bars(ctx, ax, covid, color=ctx.p.RED, label="COVID-19 (ICD-10 U07)")
    _line(ctx, ax, pneumonia, color=ctx.p.NAVY, label="pneumonia (J12-J18)", lw=2.0)
    fig.style_axis(ax)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    _headroom(ax, top=0.52)
    _legend(ctx, ax, loc="upper left")
    ctx.annotate_value(ax, 2021, covid[2021], f"{covid[2021]:,.1f}k",
                     color=ctx.p.RED)
    _note(ctx, ax, 0.98, 0.99,
         "Influenza is not on this chart because Argentina barely codes\n"
         "it: 9 to 358 deaths a year, against 15,000-40,000 pneumonias.\n"
         "A fatal flu is certified as the pneumonia it became.",
         ha="right")

    ax = fig.next_panel("All deaths, with the COVID-19 share, thousands")
    total = {y: v / 1000 for y, v in causes["deaths_total"].items()}
    other = {y: total[y] - covid.get(y, 0) for y in total}
    years = sorted(total)
    ax.bar(years, [other[y] for y in years], width=0.78, color=ctx.p.CELESTE,
           label="all other causes", zorder=2)
    ax.bar(years, [covid.get(y, 0) for y in years],
           bottom=[other[y] for y in years], width=0.78, color=ctx.p.RED,
           label="COVID-19", zorder=2)
    fig.style_axis(ax)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    _headroom(ax, top=0.70)
    _legend(ctx, ax, loc="upper left", ncol=2)
    _note(ctx, ax, 0.98, 0.99,
         "164,785 deaths in all, confirmed and probable together. The\n"
         "cause code is truncated to three characters in the published\n"
         "file, so the two cannot be separated here.", ha="right")

def plate_violence(ctx, fig) -> None:
    hom = ds.load("social/homicides.csv")
    fem = ds.load("social/femicides.csv")

    ax = fig.next_panel("Intentional homicide rate, per 100,000 people")
    _line(ctx, ax, hom["rate"], color=ctx.p.NAVY)
    fig.style_axis(ax)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.1f}"))
    _headroom(ax, top=0.22)
    peak = max(hom["rate"], key=hom["rate"].get)
    ctx.annotate_value(ax, peak, hom["rate"][peak], f"{hom['rate'][peak]:.2f}",
                     color=ctx.p.RED)
    _end_label(ctx, ax, hom["rate"], fmt="{:.2f}", color=ctx.p.NAVY)
    _note(ctx, ax, 0.40, 0.99,
         "Argentina's homicide rate is among the lowest in\n"
         "South America and has fallen by half since 2014.")

    ax = fig.next_panel("Homicide victims, count")
    _bars(ctx, ax, hom["count"], color=ctx.p.CELESTE)
    fig.style_axis(ax)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    _end_label(ctx, ax, hom["count"], fmt="{:,.0f}", color=ctx.p.CELESTE_D)

    # ---- the femicide panel ------------------------------------------
    # Three rules this panel follows deliberately, after the same panel
    # went wrong in the Brazilian edition of this atlas:
    #   1. The title names exactly what is drawn — a rate, not a share.
    #   2. Nothing here is a subset of anything else on the panel, and
    #      the one place a containment claim could be read (the counts
    #      below) says in words which number contains which.
    #   3. The caveat about the 2017 methodology change sits **at 2017**,
    #      touching the line it explains, not in a corner of the figure.
    ax = fig.next_panel("Direct femicide victims, rate per 100,000 women")
    _line(ctx, ax, fem["rate_per_100k_women"], color=ctx.p.PURPLE, lw=2.6)
    fig.style_axis(ax)
    ax.set_ylim(0, max(fem["rate_per_100k_women"].values()) * 1.75)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.2f}"))
    _end_label(ctx, ax, fem["rate_per_100k_women"], fmt="{:.2f}", color=ctx.p.PURPLE)
    first = min(fem["rate_per_100k_women"])
    ctx.annotate_value(ax, first, fem["rate_per_100k_women"][first],
                     f"{fem['rate_per_100k_women'][first]:.2f} in {first}",
                     color=ctx.p.PURPLE, offset=(4, -20), ha="left")
    ax.axvline(2017, color=ctx.p.FAINT, lw=1.0, ls=(0, (4, 3)), zorder=1)
    ax.annotate(
        "the registry's method changed in 2017;\n"
        "readings either side are not strictly comparable",
        xy=(2017, fem["rate_per_100k_women"][2017]),
        textcoords="axes fraction", xytext=(0.40, 0.95),
        fontsize=8.2, color=ctx.p.MUTED, style="italic", ha="left", va="top",
        arrowprops=dict(arrowstyle="-", color=ctx.p.FAINT, lw=0.9,
                        shrinkA=0, shrinkB=4),
        bbox=dict(boxstyle="round,pad=0.4", facecolor=ctx.p.PAPER,
                  edgecolor=ctx.p.SPINE, linewidth=0.6), zorder=8)
    _note(ctx, ax, 0.02, 0.30,
         "Flat for a decade at roughly one victim per 100,000\n"
         "women, then falling in 2024 and 2025.")

    ax = fig.next_panel("Femicide victims counted, where the registry states them")
    years = sorted(fem["direct_victims"])
    direct = [fem["direct_victims"][y] for y in years]
    linked = [fem["linked_victims"].get(y, 0) for y in years]
    ax.bar(years, direct, width=0.5, color=ctx.p.PURPLE, label="direct victims",
           zorder=2)
    ax.bar(years, linked, bottom=direct, width=0.5, color=ctx.p.SUN,
           label="linked victims, killed alongside them", zorder=2)
    # The direct count is written inside its own segment and the linked
    # count above the bar, rather than one total on top: 2025 has no
    # published linked figure, and a single number over each bar would
    # make that year's 200 look like the same quantity as 2023's 272.
    for x, d, k in zip(years, direct, linked):
        ax.text(x, d / 2, f"{d:,.0f}", ha="center", va="center",
                fontsize=11, fontweight="bold", color="white", zorder=5,
                gid="qa-on-data")  # written inside its own bar, on purpose
        if k:
            ax.text(x, d + k + 5, f"+{k:,.0f} linked", ha="center",
                    va="bottom", fontsize=8.6, color=ctx.p.MUTED, zorder=5)
    fig.style_axis(ax, xticks_years=False)
    ax.set_xlim(min(years) - 1.1, max(years) + 1.1)
    ax.set_xticks(years)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    _headroom(ax, top=0.55)
    _legend(ctx, ax, loc="upper left")
    _note(ctx, ax, 0.98, 0.99,
         "Linked victims are additional people, not a share of the\n"
         "figure below them. Only three years appear at all, because\n"
         "only three reports state a count unambiguously — the rate\n"
         "panel beside this one is complete and this one is not, and\n"
         "interpolating would invent the years it is missing.",
         ha="right")


# The plates, in the order the page lists them.
PLATES = (

    ("plate_output", plate_output),

    ("plate_prices", plate_prices),

    ("plate_living", plate_living),

    ("plate_state", plate_state),

    ("plate_trade", plate_trade),

    ("plate_credit", plate_credit),

    ("plate_markets", plate_markets),

    ("plate_people", plate_people),

    ("plate_violence", plate_violence),

)


# The plates, declared rather than described in prose inside each function.
# `alt` is the plate's alternative text: the one thing a reader using a
# screen reader gets instead of the figure, so it states the numbers the
# panels show rather than naming the chart type.
PLATES = [
    dict(id="01", slug="output", builder=plate_output,
         title="Twenty years of Argentine output",
         subtitle="Dollar GDP, real growth, income per head, 2006-2026",
         source="Source: INDEC, Cuentas Nacionales (base 2004), via "
                "apis.datos.gob.ar",
         alt="Four panels on Argentine output from 2006 to 2026. Dollar GDP "
             "rises from US$233 billion to a peak of US$656 billion in 2023 "
             "and ends near US$683 billion, but moves with the exchange rate "
             "as much as with output. Real growth alternates sharply: -5.9% "
             "in 2009, -9.9% in 2020, +10.4% in 2021, averaging close to 1% "
             "a year. GDP per capita peaks at US$14,901 in 2015 and is "
             "US$14,730 in 2025. An index of real output set to 100 in 2006 "
             "ends the window only modestly above where it began."),
    dict(id="02", slug="prices", builder=plate_prices,
         title="Prices, the peso and the two dollars",
         subtitle="Inflation, the exchange rate and reserves, 2006-2026",
         source="Sources: INDEC (national CPI, from Dec 2016); Dirección "
                "Provincial de Estadística y Censos de San Luis (2007-2016); "
                "BCRA; parallel rates via Ámbito Financiero",
         alt="Four panels on Argentine prices. Annual inflation is shown in "
             "two colours because no usable official national index exists "
             "between 2007 and 2016, the decade INDEC was intervened: the "
             "provincial San Luis index stands in, running 18% to 39% a "
             "year. The national index resumes in 2017 and peaks at 211% in "
             "2023 before falling to 31.5% in 2025 and 21.3% in 2026. The "
             "peso goes from about 3 to the dollar to roughly 1,500, drawn "
             "on a log scale against the parallel rate. The gap between the "
             "two reaches nearly 100% during the second currency control "
             "period. Central bank reserves swing between US$56 billion and "
             "US$21.9 billion in 2023, recovering to US$49.7 billion."),
    dict(id="03", slug="living", builder=plate_living,
         title="Work, wages and who is poor",
         subtitle="Unemployment, the minimum wage, poverty and inequality",
         source="Sources: INDEC, Encuesta Permanente de Hogares; Ministerio "
                "de Trabajo (SMVM); via apis.datos.gob.ar",
         alt="Four panels on Argentine living standards. Unemployment falls "
             "from 10.1% in 2006 to 6.1% in 2023, rising to about 7% after. "
             "The minimum wage in dollars peaks above US$600 around 2013-15 "
             "and is US$269 in 2025, lower than in 2006. Poverty is drawn as "
             "two lines, one per half year, with the intervened decade left "
             "blank: it reaches 52.9% in the first half of 2024 — the half "
             "after the December 2023 devaluation — and 38.1% in the second. "
             "The Gini coefficient moves in a narrow band around 0.42-0.44."),
    dict(id="04", slug="state", builder=plate_state,
         title="What the state takes and what it spends",
         subtitle="Primary balance, tax revenue and spending by function",
         source="Sources: Secretaría de Hacienda, Esquema Ahorro-Inversión-"
                "Financiamiento; Gasto Público Consolidado; via "
                "apis.datos.gob.ar",
         alt="Four panels on Argentine public finances. The primary balance "
             "is drawn as three separate segments because three incompatible "
             "methodologies cover the window; the last reaches -6.4% of GDP "
             "in 2020 and turns to a surplus of +1.78% in 2024, the first "
             "since 2010. Tax revenue runs between 21% and 26% of GDP, with "
             "export duties and income tax shown as components. Primary "
             "spending by function is stacked, dominated by pensions at 7.6% "
             "to 9.7% of GDP; the consolidated series ends in 2023. The last "
             "panel sets pensions against debt service, which peaks at 4.35% "
             "of GDP in 2019."),
    dict(id="05", slug="trade", builder=plate_trade,
         title="What Argentina sells to the world",
         subtitle="Exports, imports and the composition of sales, 2006-2026",
         source="Source: INDEC, Intercambio Comercial Argentino, via "
                "apis.datos.gob.ar",
         alt="Four panels on Argentine trade. Exports and imports both peak "
             "near US$88 billion and US$81 billion in 2022; the trade "
             "balance swings from a deficit of US$8.3 billion in 2017 to a "
             "surplus of US$18.9 billion in 2024. Exports by category are "
             "stacked: primary products, agricultural manufactures, "
             "industrial manufactures and fuel. Industrial manufactures are "
             "computed as the residual because that category's own series is "
             "served empty by the source. Fuel and energy rise as a share of "
             "exports in the most recent years."),
    dict(id="06", slug="credit", builder=plate_credit,
         title="A banking system that barely lends",
         subtitle="Credit, household debt and what money costs, 2006-2026",
         source="Source: BCRA, api.bcra.gob.ar (daily balances, December "
                "averages); system indicators via apis.datos.gob.ar",
         alt="Four panels on Argentine credit. Credit to the private sector "
             "stays between 9% and 15% of GDP across twenty years, against "
             "50-70% in Chile or Brazil; households account for roughly half "
             "of it. Mortgage lending collapses from 1.56% of GDP in 2008 to "
             "0.28% in 2024, recovering only to 0.74% in 2025. Real interest "
             "rates show saving punished every year from 2017 to 2024, the "
             "real deposit rate reaching -37% in 2023, then turning positive "
             "in 2025 while real borrowing costs rise above 30%. "
             "Non-performing loans jump from 1.54% in 2024 to 5.54% in 2025, "
             "the worst reading since 2006."),
    dict(id="07", slug="markets", builder=plate_markets,
         title="What the market charged Argentina",
         subtitle="The Merval in dollars, country risk and reserves",
         source="Market references, not official statistics: Merval and "
                "S&P 500 closes via Yahoo Finance; EMBI+ Argentina via "
                "Ámbito Financiero",
         alt="Four panels on Argentine markets. The Merval converted to "
             "dollars is indexed against the S&P 500 at 2006 equals 100 on a "
             "log scale; it outruns the American index in some periods and "
             "gives it all back in others. Country risk, the EMBI+ spread, "
             "sits near 400 basis points in 2017 and above 2,200 in 2022, "
             "falling to about 570 by 2025. The last panel sets reserves "
             "against country risk on twin axes: they move against each "
             "other almost throughout."),
    dict(id="08", slug="people", builder=plate_people,
         title="Fewer births, and one bad year of deaths",
         subtitle="Vital statistics and causes of death, 2006-2024",
         source="Source: Ministerio de Salud, DEIS — nacidos vivos, serie "
                "histórica de defunciones, and defunciones por causa (CIE-10)",
         alt="Four panels on Argentine demography. Births fall from 777,012 "
             "in 2014 to 413,135 in 2024, down 46.8% in ten years, while "
             "deaths rise; the two lines converge without crossing. Natural "
             "increase collapses from 451,000 a year to 36,700. COVID-19 "
             "deaths are 53,222 in 2020 and 84,695 in 2021, against 15,000 "
             "to 40,000 pneumonia deaths a year; influenza is excluded "
             "because Argentina codes only 9 to 358 influenza deaths a year. "
             "Total deaths peak at 436,799 in 2021, with COVID-19 shown as a "
             "stacked share; the registry records 164,785 COVID-19 deaths in "
             "all, confirmed and probable together."),
    dict(id="09", slug="violence", builder=plate_violence,
         title="Homicide and femicide",
         subtitle="Two registries, two different kinds of completeness",
         source="Sources: Ministerio de Seguridad, SNIC (homicides); Corte "
                "Suprema de Justicia, Oficina de la Mujer — Registro "
                "Nacional de Femicidios (femicides)",
         alt="Four panels on lethal violence in Argentina. The intentional "
             "homicide rate peaks at 7.62 per 100,000 in 2014 and falls to "
             "3.61 by 2025, roughly halving, among the lowest rates in South "
             "America; the victim count falls from 3,253 to 1,676. The "
             "femicide rate per 100,000 women is flat near 1.0 from 2014 to "
             "2023, then falls to 0.95 in 2024 and 0.85 in 2025; a marker at "
             "2017 notes that the registry changed its method there and "
             "readings either side are not strictly comparable. The final "
             "panel shows counted victims for only the three years the "
             "reports state them — 2023, 2024 and 2025 — with linked victims "
             "stacked above direct victims as further people killed rather "
             "than as part of the same count."),
]
