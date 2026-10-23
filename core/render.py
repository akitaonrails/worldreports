"""Render one country's plates, or every country's.

    python3 -m core.render france
    python3 -m core.render france --langs fr
    python3 -m core.render --all
    python3 -m core.render france --out /tmp/check   # without touching output/

Nothing here touches the network: every plate is drawn from the CSVs
committed under countries/<slug>/data. A missing series makes its panel
render an honest "pending" note instead of failing, so the pipeline is
always runnable.

One country is rendered at a time, in its own `Context`, with the
translation catalog rebound between countries — see core.context.render.
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

from dataclasses import dataclass

from core import context, i18n, style
from core.country import COUNTRIES_DIR, Country


@dataclass
class Plate:
    """One plate, however its country chose to declare it.

    Two shapes grew up in the five original projects and both are kept:

      ("fig_economy", fig_economy)        the function builds its own
                                          figure, titles it and saves it
      dict(id="01", slug="output",        the figure, its title and its
           builder=..., title=...,        alt text are declared here and
           subtitle=..., alt=...,         the function only draws panels
           topic="economy")

    The declarative shape is better — the title and the alt text are
    reviewable without reading the drawing code — so new countries should
    use it, and `alt` is required there because it is the only thing a
    screen-reader user gets instead of the image.

    `topic` puts a declarative plate on the spine (core/spine.py): the
    figure is built on the spine frame and the builder claims its panels
    with `ig.slot(key, title)`. A function plate passes `topic=` to
    `ctx.fig` itself. None is a plate not migrated yet.
    """

    name: str
    draw: object
    title: str | None = None
    subtitle: str | None = None
    source: str = ""
    alt: str | None = None
    filename: str | None = None
    topic: str | None = None

    @property
    def declarative(self) -> bool:
        return self.title is not None


def normalise(entries) -> list[Plate]:
    out = []
    for e in entries:
        if isinstance(e, dict):
            slug, pid = e["slug"], e.get("id")
            stem = f"{pid}-{slug}" if pid else slug
            out.append(Plate(name=e.get("builder").__name__, draw=e["builder"],
                             title=e["title"], subtitle=e.get("subtitle", ""),
                             source=e.get("source", ""), alt=e.get("alt"),
                             filename=f"{stem}.png", topic=e.get("topic")))
        else:
            name, fn = e
            out.append(Plate(name=name, draw=fn))
    return out


def load_plates(country: Country):
    """Import countries/<slug>/plates.py and return its PLATES tuple.

    Loaded by path under a private module name rather than added to
    sys.path: five countries each with a `plates` module would otherwise
    collide in sys.modules, and the second country rendered would silently
    draw the first one's plates.
    """
    path = country.dir / "plates.py"
    if not path.exists():
        raise SystemExit(f"{country.slug}: no plates.py")
    name = f"_plates_{country.slug.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    plates = getattr(module, "PLATES", None)
    if not plates:
        raise SystemExit(f"{country.slug}: plates.py defines no PLATES")
    return normalise(plates)


def draw(ctx, plate: Plate) -> None:
    """Draw and save one plate, whichever shape it was declared in.

    The one place the two shapes are told apart, so the renderer and every
    harness that replaces `Infographic.save` to look inside a plate build
    the figure the same way — the same frame, the same topic.
    """
    if plate.declarative:
        fig = ctx.fig(plate.title, plate.subtitle, source=plate.source,
                      topic=plate.topic)
        plate.draw(ctx, fig)
        fig.save(ctx.out(plate.filename))
    else:
        plate.draw(ctx)


def render_country(country: Country, langs=None, out_dir=None, only=None,
                   strict=True) -> list[str]:
    """Draw every plate for one country. Returns the problems found."""
    plates = load_plates(country)
    langs = tuple(langs or country.locale_codes)
    problems: list[str] = []

    ctx = context.Context(country, out_dir=out_dir)
    i18n.bind(country)
    for lang in langs:
        if not style.has_script_font(lang):
            problems.append(
                f"{country.slug}/{lang}: no installed font can render this "
                f"language; the plates would be written as empty boxes")
            continue
        i18n.set_lang(lang)
        i18n.reset_missing()
        print(f"--- {country.slug} / {lang} ---")
        for plate in plates:
            if only and plate.name not in only and plate.filename not in only:
                continue
            try:
                draw(ctx, plate)
            except Exception as e:  # noqa: BLE001
                problems.append(f"{country.slug}/{lang}/{plate.name}: "
                                f"{type(e).__name__}: {e}")
                print(f"  {plate.name} failed: {type(e).__name__}: {e}")
        gaps = i18n.missing()
        if gaps and strict:
            # A plate half in English is worse than one plainly in English,
            # so this is a build failure rather than a warning.
            print(f"\n  {len(gaps)} untranslated string(s) in {lang}:")
            for g in gaps:
                print(f"      {g!r}")
            problems.append(
                f"{country.slug}/{lang}: {len(gaps)} untranslated strings")
    i18n.set_lang("en")
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("country", nargs="?",
                    help="a slug under countries/, or --all")
    ap.add_argument("--all", action="store_true", help="every country")
    ap.add_argument("--langs", help="comma-separated subset of its locales")
    ap.add_argument("--out", help="write plates here instead of output/")
    ap.add_argument("--only", help="comma-separated plate function names")
    ap.add_argument("--no-strict", action="store_true",
                    help="warn about untranslated strings instead of failing")
    a = ap.parse_args(argv)

    if a.all:
        targets = Country.all()
    elif a.country:
        targets = [Country.load(a.country)]
    else:
        known = sorted(p.parent.name for p in COUNTRIES_DIR.glob("*/country.yaml"))
        ap.error(f"name a country ({', '.join(known)}) or pass --all")

    langs = [x.strip() for x in a.langs.split(",")] if a.langs else None
    only = {x.strip() for x in a.only.split(",")} if a.only else None
    out = Path(a.out) if a.out else None

    problems = []
    for c in targets:
        sub = out / c.slug if out else None
        problems += render_country(
            c, langs=[l for l in langs if l in c.locale_codes] if langs else None,
            out_dir=sub, only=only, strict=not a.no_strict)

    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
