"""Make the repository root importable from anywhere the tests are run.

    python3 -m pytest                      # everything
    python3 -m pytest countries/france     # one country
    python3 -m pytest tests/test_data.py

Country tests live beside the country they test, shared tests under
tests/, and both import `core` and `tests.probe` — which only resolves if
the root is on the path however pytest was invoked.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
