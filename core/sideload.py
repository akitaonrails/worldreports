"""Load a module that sits beside another file, by path.

`countries/south-korea` cannot be an importable package — the hyphen is not
a legal identifier — and five countries each with a module called `events`
would collide in `sys.modules` anyway, so the second country loaded would
silently get the first one's timeline. Both problems go away by loading the
file by path under a name that carries its country.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def sibling(anchor: str, name: str):
    """Import `name`.py from the directory holding `anchor`."""
    base = Path(anchor).resolve().parent
    path = base / f"{name}.py"
    if not path.exists():
        raise ModuleNotFoundError(f"{path} does not exist")
    key = f"_country_{base.name.replace('-', '_')}_{name}"
    if key in sys.modules:
        return sys.modules[key]
    spec = importlib.util.spec_from_file_location(key, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[key] = module
    spec.loader.exec_module(module)
    return module
