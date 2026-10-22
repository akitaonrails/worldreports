"""Nothing that draws one country's plate may read another country's data.

This is the rule the whole repository rests on. Five atlases that used to
be five repositories now share a checkout, and the failure mode that
matters is not a crash — it is a French number appearing on a Brazilian
plate and nobody noticing, because both are plausible.

So it is tested from three sides:

  * the boundary itself, against the paths that would escape it;
  * every country's chapter and plate code, by drawing it with the
    filesystem watched and failing on any read outside its own directory;
  * the shared code, which must not name a country at all.
"""
from __future__ import annotations

import builtins
import io
import json
from pathlib import Path

import pytest

from core import context, i18n, render, sitebuild
from core import country as country_mod
from core.country import COUNTRIES_DIR, Country, DataIsolationError, within
from core.render import load_plates


# ----------------------------------------------------------- the boundary
ESCAPES = [
    "../france/data/macro/gdp.csv",   # a sibling country, by name
    "../../core/style.py",            # the shared code
    "..",                             # the parent itself
    "a/../../b.csv",                  # climbing out through a subdirectory
    "/etc/passwd",                    # absolute
    "/",
]


@pytest.mark.parametrize("rel", ESCAPES)
def test_boundary_refuses_paths_that_escape(tmp_path, rel):
    base = tmp_path / "data"
    base.mkdir()
    with pytest.raises(DataIsolationError):
        within(base, rel, "somewhere")


def test_boundary_allows_paths_inside(tmp_path):
    base = tmp_path / "data"
    (base / "macro").mkdir(parents=True)
    assert within(base, "macro/gdp.csv") == base / "macro" / "gdp.csv"
    assert within(base, "./macro/../macro/gdp.csv") == base / "macro" / "gdp.csv"


def test_boundary_follows_symlinks_out(tmp_path):
    """A symlink is resolved before the check, not after.

    Checking the string would pass a link whose target is elsewhere, which
    is exactly how a country could be pointed at another's data by a
    convenience symlink someone left behind.
    """
    base = tmp_path / "data"
    base.mkdir()
    (tmp_path / "elsewhere").mkdir()
    (tmp_path / "elsewhere" / "gdp.csv").write_text("year\n2006\n")
    (base / "link").symlink_to(tmp_path / "elsewhere")
    with pytest.raises(DataIsolationError):
        within(base, "link/gdp.csv", "somewhere")


def test_country_accessors_refuse_another_country(country):
    others = [c for c in Country.all() if c.slug != country.slug]
    for other in others:
        with pytest.raises(DataIsolationError):
            country.data(f"../../{other.slug}/data/x.csv")
    with pytest.raises(DataIsolationError):
        country.out("../../core/style.py")


def test_country_cannot_be_loaded_from_outside_countries():
    for bad in ("../core", "..", "/etc"):
        with pytest.raises((DataIsolationError, FileNotFoundError, ValueError)):
            Country.load(bad)


# ------------------------------------------------- watching the real code
@pytest.fixture
def watch_opens(monkeypatch):
    """Record every file opened, by any means, while this is installed.

    Patching `within` alone would only prove the boundary is consulted; it
    would say nothing about code that sidesteps it. This watches `open`
    itself, plus the one Path method that reads a file without it, so a
    plate that reaches straight for a path is caught too.
    """
    seen: list[Path] = []
    real_open = builtins.open
    real_popen = Path.open

    def note(target):
        try:
            seen.append(Path(target).resolve())
        except (TypeError, ValueError, OSError):
            pass

    def spy_open(file, *a, **kw):
        note(file)
        return real_open(file, *a, **kw)

    def spy_path_open(self, *a, **kw):
        note(self)
        return real_popen(self, *a, **kw)

    monkeypatch.setattr(builtins, "open", spy_open)
    monkeypatch.setattr(Path, "open", spy_path_open)
    return seen


def _trespass(seen, country) -> list[Path]:
    """Of the files read, those belonging to another country."""
    mine = (COUNTRIES_DIR / country.slug).resolve()
    out = []
    for path in seen:
        if COUNTRIES_DIR not in path.parents:
            continue          # core, site/, the stdlib, matplotlib's data
        if mine == path or mine in path.parents:
            continue
        out.append(path)
    return out


def test_drawing_plates_reads_only_this_country(country, watch_opens, tmp_path):
    """Draw every plate for real and fail on any read outside the country.

    The plates are drawn in English only: the files a plate reads do not
    depend on the language it is labelled in, and one pass is enough to
    catch a path that points at the wrong country.
    """
    i18n.bind(country)
    i18n.set_lang("en")
    ctx = context.Context(country, out_dir=tmp_path)
    for plate in load_plates(country):
        render.draw(ctx, plate)
    bad = _trespass(watch_opens, country)
    assert not bad, (f"{country.slug}'s plates read another country's files: "
                     + ", ".join(str(p) for p in sorted(set(bad))[:6]))


def test_building_chapters_reads_only_this_country(country, watch_opens):
    """The same, for the numbers printed on the cards."""
    sitebuild.chapters_for(country)
    sitebuild.headline_for(country)
    sitebuild.datasets_for(country)
    bad = _trespass(watch_opens, country)
    assert not bad, (f"{country.slug}'s chapters read another country's "
                     f"files: " + ", ".join(str(p) for p in sorted(set(bad))[:6]))


def test_recorded_provenance_stays_inside_the_country(country):
    """Every file core.provenance recorded is one of this country's."""
    path = country.dir / "provenance.json"
    assert path.exists(), (f"{country.slug}: no provenance.json — run "
                           f"`python3 -m core.provenance {country.slug}`")
    recorded = json.loads(path.read_text(encoding="utf-8"))
    assert recorded, f"{country.slug}: provenance.json is empty"
    for plate, files in recorded.items():
        assert files, f"{country.slug}/{plate}: no file recorded"
        for rel in files:
            resolved = country.data(rel)      # raises if it escapes
            assert resolved.exists(), f"{country.slug}/{plate}: {rel} is gone"
