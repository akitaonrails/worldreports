"""Record which CSV each plate was actually drawn from, by watching it draw.

    python3 -m core.provenance --all
    python3 -m core.provenance france

A plate is a claim, and the thing that makes it checkable is knowing which
committed file it came from. Only one of the five original projects wrote
that down by hand, in a table spec per plate; the other four left it
implicit in the drawing code, where it drifts the moment a panel changes.

So it is not written down at all. Each plate is rendered with the country's
file accessors instrumented, and whatever it read is what gets recorded —
`countries/<slug>/provenance.json`, regenerated with the plates and
committed beside them. A plate that stops reading a file stops claiming it,
without anyone remembering to edit a list.

The same instrumentation answers the question the whole monorepo rests on:
did this country's plates read only this country's data? Every read goes
through `Country.data`, which refuses a path outside countries/<slug>/, and
this watches that boundary from the other side — see tests/test_isolation.py.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

from core import context, i18n, style
from core import country as country_mod
from core.country import COUNTRIES_DIR, Country, DataIsolationError
from core.render import load_plates


@contextmanager
def watching(country: Country):
    """Yield a {plate stem: sorted files} map, filled as plates are drawn.

    Two things are intercepted. `core.country.within` is the one door every
    path resolution goes through — the shared accessors and a country's own
    CSV reader alike — so it names the files; `Infographic.save` names the
    plate they belong to, because a plate's identity on the page is its
    filename and not the function that happens to draw it.

    Patching the door rather than the accessor is what makes this a
    complete record: a country that grows its own reader is watched by
    construction instead of being quietly left out.
    """
    base = country.data_dir.resolve()
    reads: set[str] = set()
    escapes: list[str] = []
    out: dict[str, list[str]] = {}
    real_within, real_save = country_mod.within, style.Infographic.save

    def within(b, rel, slug=""):
        target = real_within(b, rel, slug)
        if target.suffix and target.is_relative_to(base):
            reads.add(str(target.relative_to(base)))
        elif target.suffix and COUNTRIES_DIR in target.parents:
            # Resolved inside countries/ but not inside this country: the
            # boundary let it through because the caller handed it another
            # country's base. That is the one thing this must never miss.
            escapes.append(str(target))
        return target

    def save(self, path):
        result = real_save(self, path)
        # The stem without the language suffix: one plate, however many
        # languages it is drawn in, reads the same files.
        out.setdefault(Path(path).stem, sorted(reads))
        reads.clear()
        return result

    country_mod.within, style.Infographic.save = within, save
    try:
        yield out
    finally:
        country_mod.within, style.Infographic.save = real_within, real_save
        if escapes:
            raise DataIsolationError(
                f"{country.slug}: read {len(escapes)} path(s) under another "
                f"country: {', '.join(sorted(set(escapes))[:4])}")


def for_country(country: Country) -> dict:
    """Render every plate once, in English, purely to watch what it reads."""
    plates = load_plates(country)
    i18n.bind(country)
    i18n.set_lang("en")
    with tempfile.TemporaryDirectory() as tmp, watching(country) as seen:
        ctx = context.Context(country, out_dir=Path(tmp))
        for plate in plates:
            if plate.declarative:
                fig = ctx.fig(plate.title, plate.subtitle, source=plate.source)
                plate.draw(ctx, fig)
                fig.save(ctx.out(plate.filename))
            else:
                plate.draw(ctx)
        found = dict(seen)
    path = country.dir / "provenance.json"
    path.write_text(json.dumps(found, ensure_ascii=False, indent=1) + "\n",
                    encoding="utf-8")
    files = sorted({f for v in found.values() for f in v})
    print(f"  {country.slug}: {len(found)} plates read {len(files)} files")
    bare = [k for k, v in found.items() if not v]
    if bare:
        print(f"    no file recorded for: {', '.join(bare)}")
    return found


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("country", nargs="?")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args(argv)
    if a.all:
        targets = Country.all()
    elif a.country:
        targets = [Country.load(a.country)]
    else:
        ap.error("name a country or pass --all")
    for c in targets:
        for_country(c)
    return 0


if __name__ == "__main__":
    sys.exit(main())
