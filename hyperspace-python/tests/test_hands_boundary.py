"""The hands package is meant to be lifted out whole one day.

These are the checks that keep it liftable. They are cheap and they fail
loudly, which is the point: the boundary erodes one convenient import at
a time, and nobody notices until the day someone tries to extract it.
"""

import ast
from pathlib import Path

import pytest

PKG = Path(__file__).resolve().parents[1] / "hyperspace" / "hands"
# the instrument: no host imports allowed. panel.py is deliberately absent
# — it is the adapter to *this* host, and extracting means replacing it.
STANDALONE = ("core.py", "signal.py", "tape.py")


def _imports(path: Path):
    """(module, level) for every import in the file."""
    out = []
    for n in ast.walk(ast.parse(path.read_text())):
        if isinstance(n, ast.ImportFrom):
            out.append((n.module or "", n.level))
        elif isinstance(n, ast.Import):
            out += [(a.name, 0) for a in n.names]
    return out


@pytest.mark.parametrize("name", STANDALONE)
def test_the_instrument_imports_nothing_from_the_host(name):
    for mod, level in _imports(PKG / name):
        if level:                       # relative: only inside this package
            assert level == 1 and mod in ("signal", "core", "tape"), \
                f"{name} reaches outside the hands package: {'.' * level}{mod}"
        else:
            assert not mod.startswith("hyperspace"), f"{name} imports {mod}"


def test_the_panel_is_the_only_piece_that_knows_the_host():
    """If this fails, the adapter has spread and extraction got harder."""
    reaching = [f.name for f in PKG.glob("*.py")
                if any(lv > 1 or m.startswith("hyperspace")
                       for m, lv in _imports(f))]
    assert reaching == ["device.py", "panel.py"]


def test_the_instrument_runs_with_no_host_at_all():
    """No registry, no router, no MIDI, no SDK — it still produces values."""
    from hyperspace.hands import HandSettings, HandsIO

    class Source:                        # the whole host contract for input
        status, on = "fake", True

        def latest(self):
            palm = type("P", (), {"x": 0.0, "y": 200.0, "z": 0.0})()
            ns = type("N", (), {})
            h = ns()
            h.type, h.confidence = ns(), 1.0
            h.type.name = "Right"
            h.grab_strength = h.pinch_strength = h.grab_angle = 0.0
            h.pinch_distance = 80.0
            h.palm = ns()
            h.palm.position = h.palm.normal = h.palm.direction = palm
            h.palm.width = 90.0
            from hyperspace.hands import features
            return 1, 0.0, {"right": (features(h), 1.0)}

    io = HandsIO(HandSettings.from_config({}), {}, source=Source(), out=None)
    io.poll(1 / 60)                      # no midi, no router
    assert len(io.lanes()) == 40
    io.close()
