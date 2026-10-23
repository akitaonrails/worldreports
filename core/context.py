"""What a plate script is handed, and the only thing it is handed.

Each country's `plates.py` is a list of functions that take a `Context` and
draw one plate. The context carries that country — its data, its palette, its
year span — with every shared helper already bound to it:

    def plate_economy(ctx):
        gdp = ctx.table("macro/gdp.csv")
        f = ctx.fig("The French Economy", "Nominal size, real growth …")
        ax = f.next_panel("GDP at current prices")
        yrs, vals = ctx.series(gdp, "nominal_eur_bn")
        ctx.line(ax, yrs, vals, ctx.p.BLUE)

Binding is the point. `ctx.line` already knows this country's last full
year, so the running year is dashed without the call site repeating it;
`ctx.table` resolves under this country's data directory and refuses
anything else. A plate has no way to name another country, so it has no way
to mix in another country's numbers — which is the one property the five
merged repositories had to keep.
"""
from __future__ import annotations

from functools import partial

from core import i18n, plotting, rates, style
from core.country import Country


class Context:
    """One country, ready to draw."""

    def __init__(self, country: Country, out_dir=None):
        self.c = country
        self.p = country.palette
        self.YEARS = list(country.years)
        self.LAST_FULL_YEAR = country.last_full_year
        self._out_dir = out_dir

        # Helpers with this country's constants already applied, so a plate
        # cannot accidentally draw a partial year as a complete one.
        self.line = partial(plotting.line,
                            last_full_year=country.last_full_year)
        self.bars = partial(plotting.bars,
                            last_full_year=country.last_full_year)
        # Helpers that need no country.
        self.series = plotting.series
        self.nan = plotting.nan
        self.endlabel = plotting.endlabel
        self.source = plotting.source
        self.read_table = plotting.read_table
        self.annotate_value = plotting.annotate_value
        # Counts into the spine's shared units. See core/rates.py.
        self.per_100k = rates.per_100k
        self.per_1000 = rates.per_1000
        self.index_2006 = rates.index_2006
        self.fx_index = rates.fx_index

    # ------------------------------------------------------------- data
    def table(self, rel: str):
        """One of this country's CSVs, or None if it is not committed yet."""
        return self.c.table(rel)

    def rows(self, rel: str, key: str = "year"):
        return self.c.rows(rel, key)

    def has(self, rel: str) -> bool:
        return self.c.has(rel)

    def comments(self, rel: str) -> list[str]:
        return self.c.comments(rel)

    # -------------------------------------------------------- year logic
    def full_years(self, years, vals):
        return plotting.full_years(years, vals, self.LAST_FULL_YEAR)

    def partial_row(self, table):
        return plotting.partial_row(table, self.LAST_FULL_YEAR)

    # ----------------------------------------------------------- drawing
    def fig(self, title: str, subtitle: str, ncols: int = 2, nrows: int = 2,
            figsize=(16.0, 10.2), source: str = "", right: float = 0.955,
            topic: str | None = None) -> style.Infographic:
        """A new multi-panel figure in this country's identity.

        `topic` puts the plate on the spine (core/spine.py): the frame is
        then fixed at 2 × 2, 16 × 10.2 in, right=0.955, and the panels are
        claimed with `slot()`. Leave it None for a plate not migrated yet.
        The default `right` leaves room for a right-hand axis label.
        """
        return style.Infographic(self.c, title, subtitle, ncols=ncols,
                                 nrows=nrows, figsize=figsize, source=source,
                                 right=right, topic=topic)

    def pending(self, ax) -> None:
        plotting.pending(ax, self.p)

    def recessions(self, fig, ax, label: bool = False) -> None:
        fig.add_recessions(ax, label=label)

    # ------------------------------------------------------------ output
    @property
    def out_dir(self):
        return self._out_dir or self.c.out_dir

    def out(self, name: str):
        if self._out_dir is not None:
            self._out_dir.mkdir(parents=True, exist_ok=True)
            return self._out_dir / name
        return self.c.out(name)
