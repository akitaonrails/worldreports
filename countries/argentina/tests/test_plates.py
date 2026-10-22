"""Argentina's plates: the registry, the alt text, and what the panels say.

The generic checks — isolation, catalogs, data hygiene, layout, the built
pages — run against every country from tests/. What is here is what only
this atlas can be asked.
"""
from __future__ import annotations

import pytest

from core.country import Country
from core.render import load_plates
from core.sideload import sibling
from tests.probe import plate

SLUG = "argentina"
COUNTRY = Country.load(SLUG)
plates = sibling(str(COUNTRY.dir / "plates.py"), "plates")
datasets = sibling(str(COUNTRY.dir / "datasets.py"), "datasets")
IDS = [p["id"] for p in plates.PLATES]


def test_nine_plates_with_unique_ids_and_slugs():
    assert len(plates.PLATES) == 9
    assert len(set(IDS)) == 9
    assert len({p["slug"] for p in plates.PLATES}) == 9
    assert IDS == sorted(IDS), "the plates are numbered out of order"


@pytest.mark.parametrize("spec", plates.PLATES, ids=IDS)
def test_every_plate_describes_itself(spec):
    """`alt` is what a screen-reader user gets instead of the plate, so it
    has to carry the findings rather than repeat the title.

    Argentina is the only one of the five whose plates were written with
    hand-authored alt text from the start. It is the standard the others
    are generated against — see core.sitebuild.describe.
    """
    for key in ("title", "subtitle", "source", "alt"):
        assert spec[key].strip(), f"{spec['id']}: {key} is empty"
    assert len(spec["alt"]) > 300, "alt text too short to replace the plate"
    assert spec["alt"] != spec["title"]
    assert any(c.isdigit() for c in spec["alt"]), "alt text quotes no figures"


def test_every_panel_of_every_plate_is_filled():
    """A four-panel grid with an empty quadrant ships as a blank white box.

    Nothing raises when a plate draws three of its four panels: the fourth
    is simply empty paper, and the reader is left to wonder what was meant
    to be there.
    """
    for spec in plates.PLATES:
        figure = plate(SLUG, spec["builder"].__name__)
        drawn = [p for p in figure.panels()
                 if p.ax.has_data() or p.texts()]
        assert len(drawn) == len(figure.panels()), \
            f"{spec['id']}: {len(figure.panels()) - len(drawn)} empty panel(s)"


def test_the_renderer_and_the_registry_agree():
    assert {p.name for p in load_plates(COUNTRY)} == \
        {p["builder"].__name__ for p in plates.PLATES}


def test_the_reader_refuses_another_countrys_data():
    """This country keeps its own CSV reader, so it needs its own proof
    that the reader is bounded — the shared accessors' test does not
    cover a path that never goes through them."""
    from core.country import DataIsolationError

    for escape in ("../../france/data/macro/gdp.csv", "/etc/passwd", ".."):
        with pytest.raises(DataIsolationError):
            datasets.path(escape)


@pytest.mark.parametrize("name", [p["builder"].__name__ for p in plates.PLATES],
                         ids=IDS)
def test_nothing_is_clipped(name):
    """A hardcoded set_ylim silently hides data once the series grows past
    it: the line leaves the top of the panel and the reader never learns a
    peak is missing."""
    for panel in plate(SLUG, name).panels():
        panel.nothing_is_clipped(slack=1e-6)
