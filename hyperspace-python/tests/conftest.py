"""Shared fixtures.

Every test runs with ``HYPERSPACE_HOME`` pointed at its own tmp_path
(audit L7), so nothing can read or write the owner's ~/Hyperspace by
accident — a test that needs a specific home still sets the variable
itself, on top of this. ``library.home()`` reads the variable on every
call, so there is no cache to clear.
"""

import os

import pytest


@pytest.fixture(autouse=True)
def _library_home(tmp_path):
    # set in os.environ directly, not through monkeypatch: a test that calls
    # monkeypatch.undo() mid-way would otherwise drop the variable and run
    # its remaining lines against the owner's real home
    before = os.environ.get("HYPERSPACE_HOME")
    os.environ["HYPERSPACE_HOME"] = str(tmp_path / "home")
    yield
    if before is None:
        os.environ.pop("HYPERSPACE_HOME", None)
    else:
        os.environ["HYPERSPACE_HOME"] = before


@pytest.fixture(autouse=True)
def _no_undo_left_installed():
    """`undo.install` is one per process (the app has one Undo): a test
    that installs one must not leave it for the next test's push sites."""
    yield
    from hyperspace import undo

    undo.install(None)


def opened_last(home, show: str = "house"):
    """A home whose last opened show is `show` (library.LAST_SHOW) — what
    the tests written against the house moods, the factory default until
    plan 14 WP3 made the party show the one a fresh home opens, stand on."""
    from pathlib import Path

    home = Path(home)
    home.mkdir(parents=True, exist_ok=True)
    (home / "last_show").write_text(f"{show}\n")
    return home
