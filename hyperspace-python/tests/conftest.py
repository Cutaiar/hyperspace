"""Shared fixtures.

Every test runs with ``HYPERSPACE_HOME`` pointed at its own tmp_path
(audit L7), so nothing can read or write the owner's ~/Hyperspace by
accident — a test that needs a specific home still sets the variable
itself, on top of this. ``library.home()`` reads the variable on every
call, so there is no cache to clear.
"""

import pytest


@pytest.fixture(autouse=True)
def _library_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HYPERSPACE_HOME", str(tmp_path / "home"))
