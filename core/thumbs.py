"""Downscale each plate to a card-sized thumbnail.

    python3 -m core.thumbs france
    python3 -m core.thumbs --all

The index cards used to show only a sparkline, which meant the page carried
no image of the thing it is an index of: nothing for an image crawler to
find, and nothing for a reader to recognise before clicking. A full plate is
2720px wide and 300KB, so ten of them above the fold is not an option
either — hence a 560px copy per plate per language, quantized to a
128-colour palette. A plate is flat line art on one paper colour, so the
palette costs nothing visible and turns a 71KB thumbnail into a 25KB one;
across ten cards in three languages that is the difference between a page
that loads on a phone and one that does not.

Thumbnails go to countries/<slug>/output/thumbs/ beside the plates they are
made from, and are committed with them: the page needs them, so the page
should not need a build step to have them.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

from core.country import Country

WIDTH = 560
PALETTE = 128


def thumb(src: Path, dest: Path) -> tuple[int, int]:
    with Image.open(src) as im:
        h = round(im.height * WIDTH / im.width)
        # LANCZOS rather than the default: a plate is thin lines and small
        # type, and a box filter turns both into grey mush at a quarter size.
        small = im.convert("RGB").resize((WIDTH, h), Image.LANCZOS)
        small = small.quantize(colors=PALETTE, method=Image.MEDIANCUT,
                               dither=Image.FLOYDSTEINBERG)
        dest.parent.mkdir(parents=True, exist_ok=True)
        small.save(dest, "PNG", optimize=True)
        return WIDTH, h


def for_country(country: Country) -> int:
    """Thumbnail every plate this country has rendered, in every language.

    English plates carry the plain filename and the others a language
    suffix, which is the same rule `Infographic.save` writes them by, so a
    stem with a dot in it is a translated plate and not a new one.
    """
    out = country.dir / "output"
    plates = sorted(p for p in out.glob("*.png") if "." not in p.stem)
    if not plates:
        print(f"{country.slug}: no plates in output/ — render them first")
        return 0
    made = 0
    for plate in plates:
        for lang in country.locale_codes:
            suffix = "" if lang == "en" else f".{lang}"
            src = out / f"{plate.stem}{suffix}.png"
            if not src.exists():
                continue
            thumb(src, out / "thumbs" / f"{plate.stem}{suffix}.png")
            made += 1
    total = sum(p.stat().st_size for p in (out / "thumbs").glob("*.png"))
    print(f"  {country.slug}: {made} thumbnails, {WIDTH}px wide, "
          f"{total / 1024:,.0f}KB total")
    return made


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
    made = sum(for_country(c) for c in targets)
    return 0 if made else 1


if __name__ == "__main__":
    sys.exit(main())
