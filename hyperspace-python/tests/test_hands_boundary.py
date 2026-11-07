"""The hands package is meant to be lifted out whole one day.

These are the checks that keep it liftable. They are cheap and they fail
loudly, which is the point: the boundary erodes one convenient import at
a time, and nobody notices until the day someone tries to extract it.
"""

import pytest
from walls import family, imports, inside, module_of, shown

# the adapters to *this* host: extracting means replacing them. Everything else
# in the package is the instrument, a new file included: no host imports allowed.
ADAPTERS = ("device", "panel")
FILES = family("hands")
INSTRUMENT = [f for f in FILES if not any(a in module_of(f)[1:2] for a in ADAPTERS)]


@pytest.mark.parametrize("path", INSTRUMENT, ids=shown)
def test_the_instrument_imports_nothing_from_the_host(path):
    for mod, level in imports(path):
        if level:                       # relative: only inside this package, never an adapter
            where = inside(path, mod, level) or ()
            assert where[:1] == ("hands",) and where[1:2] and where[1] not in ADAPTERS, \
                f"{shown(path)} reaches outside the instrument: {'.' * level}{mod}"
        else:
            assert not mod.startswith("hyperspace"), f"{shown(path)} imports {mod}"


def test_the_panel_is_the_only_piece_that_knows_the_host():
    """If this fails, the adapter has spread and extraction got harder."""
    reaching = [shown(f) for f in FILES
                if any((inside(f, m, lv) or ("",))[0] != "hands" if lv
                       else m.startswith("hyperspace") for m, lv in imports(f))]
    assert reaching == ["hands/device.py", "hands/panel.py"]


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
    assert len(io.lanes()) == 46
    io.close()
