"""
conftest.py
===========
Ensure our shim packages (thumbhash, blurhash, colorthief) are always imported
from python/ rather than from any identically-named packages that may be
installed in the venv (e.g. ``thumbhash-python``, ``blurhash-python``).

This is needed when competitor packages are installed for benchmarking.
"""

import sys
from pathlib import Path

_PYTHON_SRC = str(Path(__file__).parent / "python")

# Guarantee our source tree is at the very front of sys.path.
if _PYTHON_SRC in sys.path:
    sys.path.remove(_PYTHON_SRC)
sys.path.insert(0, _PYTHON_SRC)
