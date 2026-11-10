"""Moved to `hyperspace/dkit/menu.py`: the kit is a package the panel imports.

This name stays so the kit's own tools — its tests, the gallery, the
dashboard, the oracles — keep their bare ``import menu``: the module that
import returns IS the package's (this file swaps itself out of
``sys.modules``), so a monkeypatch on one is a monkeypatch on the other.
"""

import sys

from hyperspace.dkit import menu as _m

sys.modules[__name__] = _m
