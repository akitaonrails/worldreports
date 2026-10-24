"""A stack without its key is colours, not a chart.

Issue #3: Japan's `_finish` stripped every in-panel legend, and the COFOG
spending stack published as seven layers nobody could name. Every other
country kept its keys. This holds the class across the atlas: a panel that
draws named stacked layers must draw the legend that names them.

Only *labelled* PolyCollections count. `fill_between` shading bands carry
no label and ask nothing of the reader; a stackplot layer the chart script
bothered to name is a series whose key was meant to be shown.
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
from matplotlib.collections import PolyCollection  # noqa: E402

from tests import probe  # noqa: E402


def named_stack_layers(panel) -> list[str]:
    """The labels of a panel's named stacked-area layers."""
    return [c.get_label() for c in panel.ax.collections
            if isinstance(c, PolyCollection)
            and not c.get_label().startswith("_")]


def test_a_stacked_panel_names_its_layers(country):
    try:
        bad = []
        for name in probe.plate_names(country.slug):
            for panel in probe.plate(country.slug, name).panels():
                layers = named_stack_layers(panel)
                if len(layers) < 2:
                    continue
                where = f"{name}/{panel.title!r}"
                key = panel.legend_labels()
                if not key:
                    bad.append(f"{where}: {len(layers)} named stacked "
                               "layers and no legend")
                elif not all(label in key for label in layers):
                    bad.append(f"{where}: legend {key} does not name "
                               f"{sorted(set(layers) - set(key))}")
        assert not bad, f"{country.slug}:\n  " + "\n  ".join(bad)
    finally:
        probe.close_all()
