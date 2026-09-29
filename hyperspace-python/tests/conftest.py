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


def opened_last(home, show: str = "house"):
    """A home whose last opened show is `show` (library.LAST_SHOW) — what
    the tests written against the house moods, the factory default until
    plan 14 WP3 made the party show the one a fresh home opens, stand on."""
    from pathlib import Path

    home = Path(home)
    home.mkdir(parents=True, exist_ok=True)
    (home / "last_show").write_text(f"{show}\n")
    return home
