"""What a plate drew, written down beside it so the viewer can read it out.

The readout shows a reader the value behind a bar or a line at a year, so it
must be the value that was drawn: these tests draw small figures and read
them back, then check the files a real render leaves.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import matplotlib
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from core import hover, spine  # noqa: E402
from core.country import Country  # noqa: E402

YEARS = [2010, 2011, 2012, 2013]


def panel(draw):
    fig, ax = plt.subplots()
    draw(ax)
    ax.set_xlim(2009, 2014)
    return fig, ax


def test_a_line_is_read_back_year_by_year():
    fig, ax = panel(lambda a: a.plot(YEARS, [1, 2, 3, 4], label="Rate", color="#112233"))
    out = hover.panel(ax)
    s = out["series"][0]
    assert (s["kind"], s["name"], s["color"]) == ("line", "Rate", "#112233")
    assert s["pts"] == [[2010, 1], [2011, 2], [2012, 3], [2013, 4]]
    assert out["xlim"] == [2009, 2014] and not out["log"]
    plt.close(fig)


def test_a_dashed_part_year_joins_the_line_it_continues():
    def draw(a):
        a.plot(YEARS[:3], [1, 2, 3], label="Rate", color="#112233")
        a.plot(YEARS[2:], [3, 4], color="#999999", ls="--")
    fig, ax = panel(draw)
    series = hover.panel(ax)["series"]
    assert len(series) == 1
    assert [p[0] for p in series[0]["pts"]] == YEARS
    plt.close(fig)


def test_bars_read_as_their_signed_height_at_their_centre():
    fig, ax = panel(lambda a: a.bar(YEARS, [2, -1, 3, 0.5], width=0.8))
    s = hover.panel(ax)["series"][0]
    assert s["kind"] == "bar"
    assert s["pts"] == [[2010, 2], [2011, -1], [2012, 3], [2013, 0.5]]
    plt.close(fig)


def test_bars_on_their_side_have_no_year_and_are_not_read():
    fig, ax = plt.subplots()
    ax.barh([0, 1, 2], [3, 5, 2])
    ax.set_xlim(2009, 2014)
    assert hover.panel(ax) is None
    plt.close(fig)


def test_a_stack_reads_as_layers_and_a_band_as_its_two_edges():
    def draw(a):
        a.stackplot(YEARS, [1, 1, 2, 2], [2, 2, 2, 3], labels=["a", "b"])
        a.fill_between(YEARS, [5, 5, 6, 6], [7, 7, 8, 8], label="band")
    fig, ax = panel(draw)
    by = {s["name"]: s for s in hover.panel(ax)["series"]}
    assert by["a"]["kind"] == by["b"]["kind"] == "layer"
    assert by["b"]["pts"][3] == [2013, 3]            # its thickness, not its top
    assert by["band"]["kind"] == "band"
    assert by["band"]["pts"][0] == [2010, 5, 7]
    plt.close(fig)


def test_a_stepped_band_reads_its_own_year_not_a_mix_of_two():
    """A tolerance band that steps every year has two corners at each step;
    the year between the steps must read the level drawn over it."""
    levels = [(2.0, 6.0), (3.0, 5.0), (1.0, 4.0)]
    def draw(a):
        a.fill_between([2010, 2011, 2012], [l for l, _ in levels],
                       [h for _, h in levels], step="mid", label="band")
    fig, ax = panel(draw)
    band = hover.panel(ax)["series"][0]
    assert band["kind"] == "band"
    assert [p for p in band["pts"] if p[0] in (2010, 2011, 2012)] == [
        [2010, 2.0, 6.0], [2011, 3.0, 5.0], [2012, 1.0, 4.0]]
    plt.close(fig)


def test_bars_take_their_name_from_the_legends_swatch():
    from matplotlib.patches import Patch

    def draw(a):
        a.bar(YEARS, [2, -1, 3, 0.5])
        a.legend(handles=[Patch(color="#aa0000"), ], labels=["Overall balance"])
    fig, ax = panel(draw)
    bars = hover.panel(ax)["series"][0]
    assert (bars["kind"], bars["name"]) == ("bar", "Overall balance")
    plt.close(fig)


def test_grouped_bars_are_read_by_group_with_every_series_in_it():
    def draw(a):
        import numpy as np
        xs = np.arange(2)
        a.bar(xs - 0.2, [5, 3], width=0.4, label="Oil", color="#111111")
        a.bar(xs + 0.2, [4, 6], width=0.4, label="Soy", color="#00aa00")
        a.set_xticks(xs)
        a.set_xticklabels(["2006", "2010"])
    fig, ax = plt.subplots()
    draw(ax)
    out = hover.panel(ax)
    assert out["groups"] == [[0, "2006"], [1, "2010"]]
    by = {s["name"]: s["pts"] for s in out["series"]}
    assert by["Oil"] == [[-0.2, 5], [0.8, 3]]
    assert by["Soy"] == [[0.2, 4], [1.2, 6]]
    plt.close(fig)


def test_a_panel_without_a_calendar_axis_is_not_read():
    fig, ax = plt.subplots()
    ax.plot([0, 1, 2], [1, 2, 3])
    assert hover.panel(ax) is None
    plt.close(fig)


def test_where_the_axes_sit_is_a_share_of_the_picture_from_its_top_left():
    fig, ax = panel(lambda a: a.plot(YEARS, [1, 2, 3, 4]))
    fig.subplots_adjust(left=0.1, right=0.6, top=0.9, bottom=0.2)
    assert hover.panel(ax)["box"] == [0.1, 0.1, 0.5, 0.7]
    plt.close(fig)


def test_only_claimed_panels_are_written_by_slot_key(tmp_path):
    fig, (a, b) = plt.subplots(1, 2)
    for ax in (a, b):
        ax.plot(YEARS, [1, 2, 3, 4])
        ax.set_xlim(2009, 2014)
    a.spine_slot = SimpleNamespace(key="topic.one")
    path = hover.write(tmp_path / "01_x.pt.png", [a, b])
    assert path.name == "01_x.pt.hover.json"
    assert list(json.loads(path.read_text())) == ["topic.one"]
    plt.close(fig)


def test_nothing_is_written_for_a_plate_with_no_readable_panel(tmp_path):
    fig, ax = plt.subplots()
    ax.spine_slot = SimpleNamespace(key="topic.one")
    assert hover.write(tmp_path / "x.png", [ax]) is None
    assert not list(tmp_path.iterdir())
    plt.close(fig)


def test_a_real_plate_leaves_a_readout_in_each_language():
    out = Country.load("brasil").dir / "output"
    for name in ("01_economy", "01_economy.pt"):
        data = json.loads((out / f"{name}.hover.json").read_text())
        assert set(data) == {s.key for s in spine.slots("economy")}
        growth = data["economy.growth"]["series"][0]["pts"]
        assert [2010, 7.5] in growth
