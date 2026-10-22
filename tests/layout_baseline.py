"""Re-record tests/layout_baseline.json.

    python3 -m tests.layout_baseline

The baseline is the number of layout faults each country currently carries
per language — see tests/test_layout.py for why they are counted rather
than forbidden. Re-record only when a change to the plates was deliberate,
and read the diff: a count going up is the thing the test exists to catch.
"""
from __future__ import annotations

import collections
import json

from core import style
from core.country import Country
from tests.test_layout import BASELINE, faults


def main() -> int:
    out = {}
    for c in Country.all():
        for lang in c.locale_codes:
            if not style.has_script_font(lang):
                print(f"  {c.slug}/{lang}: skipped, no font for this script")
                continue
            counts = collections.Counter(f.split()[1]
                                         for f in faults(c.slug, lang))
            out[f"{c.slug}/{lang}"] = dict(sorted(counts.items()))
            print(f"  {c.slug}/{lang}: {dict(counts) or 'clean'}")
    BASELINE.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(f"\nwrote {BASELINE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
