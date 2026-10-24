"""placement.py: where the two windows open at launch (plan 16 WP4).

Fake screens throughout — no window system. The laptop is the primary
screen; the projector sits to its right.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from hyperspace import placement
from hyperspace.placement import FILE, MARGIN, SCHEMA, Screen, place

RENDER = (1280, 820)       # app.RENDER_SIZE / CONTROL_SIZE, spelled out: the
CONTROL = (960, 900)       # first-launch test holds today's numbers
LAPTOP = Screen("Built-in Retina Display", 0, 38, 1728, 1041)
PROJECTOR = Screen("DELL U2720Q", 1728, 0, 1920, 1080)
BOTH = [LAPTOP, PROJECTOR]


def entry(x, y, w, h, screen=""):
    return {"x": x, "y": y, "w": w, "h": h, "screen": screen}


# ---- the case table ----

def test_first_launch_places_as_before():
    """No file, default config, one screen: the spots app._windows used
    before this module — render at the work area + 16, controls flush
    right − 16 — at the two constants' sizes, and nothing to say."""
    x, y, w, _ = LAPTOP.x, LAPTOP.y, LAPTOP.w, LAPTOP.h
    assert place("render", RENDER, [LAPTOP], -1, None) == ((x + 16, y + 16, 1280, 820), "")
    assert place("control", CONTROL, [LAPTOP], -1, None) == (
        (max(x + w - 960 - 16, x + 16), y + 16, 960, 900), "")
    # a screen narrower than the control window: it starts at the margin, as before
    small = Screen("small", 0, 25, 900, 1000)
    assert place("control", CONTROL, [small], -1, None)[0][:2] == (16, 41)
    # and an empty file is a first launch
    assert place("render", RENDER, [LAPTOP], -1, {}.get("render"))[0] == (16, 54, 1280, 820)


def test_a_remembered_rect_is_restored():
    r, note = place("render", RENDER, BOTH, -1, entry(1900, 120, 1000, 700, PROJECTOR.name))
    assert r == (1900, 120, 1000, 700) and note == ""          # position and size
    c, note = place("control", CONTROL, BOTH, -1, entry(300, 90, 800, 850, LAPTOP.name))
    assert c == (300, 90, 800, 850) and note == ""


def test_a_rect_on_a_screen_that_is_gone_falls_back():
    """Two screens saved, one connected: the default spot on the primary,
    and a note naming the screen that is missing."""
    r, note = place("render", RENDER, [LAPTOP], -1, entry(1900, 120, 1280, 820, PROJECTOR.name))
    assert r == placement.default_rect("render", RENDER, LAPTOP)
    assert PROJECTOR.name in note and "not connected" in note and LAPTOP.name in note


def test_an_off_screen_rect_falls_back():
    default = placement.default_rect("render", RENDER, LAPTOP)
    mw, mh = placement.MIN_VISIBLE
    # overlap under MIN_VISIBLE: only a sliver at the right edge, or at the bottom
    sliver = (LAPTOP.x + LAPTOP.w - (mw - 1), 100, 1280, 820)
    low = (100, LAPTOP.y + LAPTOP.h - (mh - 1), 1280, 820)
    # a top edge above the work area: the title bar is under the menu bar or off the top
    above = (100, LAPTOP.y - 40, 1280, 820)
    for bad in (sliver, low, above, (-5000, -5000, 1280, 820)):
        assert not placement.usable(bad, [LAPTOP])
        r, note = place("render", RENDER, [LAPTOP], -1, entry(*bad))
        assert r == default and "on no screen" in note
    # just enough showing is enough
    ok = (LAPTOP.x + LAPTOP.w - mw, LAPTOP.y + LAPTOP.h - mh, 1280, 820)
    assert placement.usable(ok, [LAPTOP])
    assert place("render", RENDER, [LAPTOP], -1, entry(*ok)) == (ok, "")


def test_a_config_monitor_beats_the_remembered_screen():
    """Fork F4 (a): `monitor = 1` with the last position on screen 0 opens
    at the default spot on screen 1."""
    r, note = place("render", RENDER, BOTH, 1, entry(200, 100, 1000, 700, LAPTOP.name))
    assert r == (PROJECTOR.x + MARGIN, PROJECTOR.y + MARGIN, 1280, 820) and note == ""
    c, _ = place("control", CONTROL, BOTH, 1, entry(200, 100, 800, 850, LAPTOP.name))
    assert c == (PROJECTOR.x + PROJECTOR.w - 960 - MARGIN, PROJECTOR.y + MARGIN, 960, 900)
    # and with no file at all
    assert place("render", RENDER, BOTH, 1, None)[0][:2] == (PROJECTOR.x + 16, 16)


def test_a_remembered_rect_on_the_configured_screen_is_kept():
    r, note = place("render", RENDER, BOTH, 1, entry(1900, 120, 1000, 700, PROJECTOR.name))
    assert r == (1900, 120, 1000, 700) and note == ""


def test_a_config_monitor_that_is_not_there_is_a_note():
    """Treated as −1: the last position if there is one, else the primary."""
    r, note = place("render", RENDER, BOTH, 2, entry(1900, 120, 1000, 700, PROJECTOR.name))
    assert r == (1900, 120, 1000, 700)
    assert note == ("config: [output] monitor = 2, but 2 screens are connected (0–1) — "
                    "using the last position")
    c, note = place("control", CONTROL, [LAPTOP], 1, None)
    assert c == placement.default_rect("control", CONTROL, LAPTOP)
    assert "control_monitor = 1" in note and "1 screen is connected (0)" in note
    # a key that is not a number at all is the same case, said
    r, note = place("render", RENDER, BOTH, "projector", None)
    assert r == placement.default_rect("render", RENDER, LAPTOP) and "not a screen index" in note
    for odd in (float("nan"), float("inf"), None, [1]):
        assert "not a screen index" in place("render", RENDER, BOTH, odd, None)[1]
    # what int() reads is read the same way app._make_output reads it
    for one in (1.0, "1", True):
        assert place("render", RENDER, BOTH, one, None) == (
            placement.default_rect("render", RENDER, PROJECTOR), "")
    # below −1 is −1
    assert place("render", RENDER, BOTH, -7, None) == (
        placement.default_rect("render", RENDER, LAPTOP), "")


def test_what_names_a_later_output_in_the_notes():
    """Plan 21 WP3: `place` is called once per render output; `what`
    ("output 2 (projector)") names it in the notes and changes nothing else."""
    gone = entry(1900, 120, 1000, 700, PROJECTOR.name)
    for args in ((2, gone), (-1, {"x": "a"}), (-1, gone)):
        scr = BOTH if args[1] is not gone or args[0] == 2 else [LAPTOP]
        plain = place("render", RENDER, scr, *args)
        named = place("render", RENDER, scr, *args, what="output 2 (projector)")
        assert named[0] == plain[0] and plain[1] and "output 2 (projector)" in named[1]
        assert "[output] monitor" not in named[1] and "render window" not in named[1]


def test_a_remembered_size_is_clipped_to_its_screen():
    r, _ = place("render", RENDER, BOTH, -1, entry(1800, 40, 5000, 3000, PROJECTOR.name))
    assert r == (1800, 40, PROJECTOR.w, PROJECTOR.h)
    # never under 320 × 240
    r, _ = place("render", RENDER, BOTH, -1, entry(1800, 40, 10, 10, PROJECTOR.name))
    assert r == (1800, 40, 320, 240)
    # the default size is not clipped — as before this module, and so a
    # small screen's size is never what gets remembered
    tiny = Screen("tiny", 0, 0, 800, 600)
    assert placement.default_rect("render", RENDER, tiny) == (16, 16, 1280, 820)
    # …but the control window's width is: two panes side by side are
    # wider than a laptop, and the desk gives up the width (ui.panel_w)
    assert placement.default_rect("control", (2372, 900), LAPTOP) == (16, 54, 1696, 900)
    assert placement.default_rect("control", (2372, 900), tiny) == (16, 16, 768, 900)
    # a huge rect that the clip would push off its screen is not used
    far = entry(PROJECTOR.x - 4000, 40, 5000, 900)
    r, note = place("render", RENDER, [PROJECTOR], -1, far)
    assert r == placement.default_rect("render", RENDER, PROJECTOR) and note


# ---- the file ----

def test_save_round_trips_and_render_is_a_list(tmp_path):
    placement.save(tmp_path, (300, 90, 960, 900), [(1900, 120, 1280, 820)], BOTH)
    doc = json.loads((tmp_path / FILE).read_text())
    assert doc == {
        "schema": SCHEMA,
        "control": {"x": 300, "y": 90, "w": 960, "h": 900, "screen": LAPTOP.name},
        "render": [{"x": 1900, "y": 120, "w": 1280, "h": 820, "screen": PROJECTOR.name}],
    }
    assert SCHEMA == "hyperspace.windows/1" and FILE == "windows.json"
    assert isinstance(doc["render"], list) and len(doc["render"]) == 1
    assert placement.load(tmp_path) == doc
    assert not list(tmp_path.glob("*.tmp"))                    # atomic: nothing left behind
    # and what was saved is what opens
    assert place("control", CONTROL, BOTH, -1, doc["control"]) == ((300, 90, 960, 900), "")
    assert place("render", RENDER, BOTH, -1, doc["render"][0]) == ((1900, 120, 1280, 820), "")
    # a second output is a second entry in the same schema (plan 21)
    placement.save(tmp_path, None, [(1900, 120, 1280, 820), (10, 60, 640, 480)], BOTH)
    doc = placement.load(tmp_path)
    assert [e["screen"] for e in doc["render"]] == [PROJECTOR.name, LAPTOP.name]
    assert doc["schema"] == SCHEMA


def test_a_none_keeps_the_old_entry(tmp_path):
    """A minimised window has no rect worth keeping: its entry stays."""
    placement.save(tmp_path, (300, 90, 960, 900), [(1900, 120, 1280, 820)], BOTH)
    placement.save(tmp_path, None, [(50, 60, 1280, 820)], BOTH)
    doc = placement.load(tmp_path)
    assert doc["control"]["x"] == 300 and doc["render"][0]["x"] == 50
    placement.save(tmp_path, (310, 90, 960, 900), [None], BOTH)
    doc = placement.load(tmp_path)
    assert doc["control"]["x"] == 310 and doc["render"][0]["x"] == 50
    # so does a rect no launch would restore: the OS's own fullscreen (the
    # content area above the work area), or a window off every screen
    placement.save(tmp_path, (0, 0, 1728, 1117), [(9000, 9000, 1280, 820)], BOTH)
    assert placement.load(tmp_path) == doc
    # nothing before it to keep: the slot is empty, and an empty slot is a first launch
    other = tmp_path / "other"
    other.mkdir()
    placement.save(other, None, [None], BOTH)
    doc = placement.load(other)
    assert doc["control"] is None and doc["render"] == [None]
    assert place("render", RENDER, BOTH, -1, doc["render"][0]) == (
        placement.default_rect("render", RENDER, LAPTOP), "")


@pytest.mark.parametrize("text", [
    "not json {",
    "[1, 2, 3]",
    '"windows"',
    json.dumps({"schema": "hyperspace.windows/2", "render": [entry(100, 100, 800, 600)]}),
    json.dumps({"render": [entry(100, 100, 800, 600)]}),                 # no schema
    json.dumps({"schema": SCHEMA, "render": entry(100, 100, 800, 600)}),  # not a list
])
def test_a_bad_file_is_ignored(tmp_path, text):
    (tmp_path / FILE).write_text(text)
    assert placement.load(tmp_path) == {}


def test_a_bad_file_is_ignored_entry_by_entry(tmp_path):
    """Wrong types inside a well-formed file: that window opens at its
    default spot (with a note), the other still where it was."""
    assert placement.load(tmp_path) == {}                      # no file at all
    default = placement.default_rect("render", RENDER, LAPTOP)
    for bad in ("left", 7, [1, 2, 3, 4], {}, {"x": 1, "y": 2},
                entry("100", 100, 800, 600), entry(True, 100, 800, 600),
                entry(100, 100, 0, 600), entry(100, 100, 800, -600),
                entry(float("nan"), 100, 800, 600), entry(float("inf"), 100, 800, 600),
                entry(10 ** 30, 100, 800, 600), entry(100, 10 ** 400, 800, 600)):
        (tmp_path / FILE).write_text(json.dumps(
            {"schema": SCHEMA, "control": entry(300, 90, 960, 900), "render": [bad]}))
        doc = placement.load(tmp_path)
        r, note = place("render", RENDER, [LAPTOP], -1, doc["render"][0])
        assert r == default and "not a rect" in note, bad
        assert place("control", CONTROL, [LAPTOP], -1, doc["control"])[0] == (300, 90, 960, 900)


def test_an_unwritable_home_costs_only_the_memory(tmp_path, capsys):
    gone = tmp_path / "no-such-folder"
    placement.save(gone, (300, 90, 960, 900), [(1900, 120, 1280, 820)], BOTH)   # no raise
    assert not gone.exists()                                   # and no folder made
    assert "could not write" in capsys.readouterr().err
    # a home whose windows.json cannot be replaced (it is a folder): the same
    (tmp_path / FILE).mkdir()
    placement.save(tmp_path, (300, 90, 960, 900), [(1900, 120, 1280, 820)], BOTH)
    assert (tmp_path / FILE).is_dir() and not list(tmp_path.glob("*.tmp"))
    assert placement.load(tmp_path) == {}


# ---- the screens ----

class _Glfw:
    def __init__(self, mons):
        self.mons = mons

    def get_monitors(self):
        return list(self.mons)

    def get_monitor_workarea(self, m):
        return self.mons[m]

    def get_monitor_name(self, m):
        return m.encode()              # pyGLFW hands back bytes


def test_screens_reads_the_work_areas_in_monitor_order():
    g = _Glfw({"Built-in": (0, 38, 1728, 1041), "DELL": (1728, 0, 1920, 1080)})
    assert placement.screens(g) == [Screen("Built-in", 0, 38, 1728, 1041),
                                    Screen("DELL", 1728, 0, 1920, 1080)]
    assert placement.screens(_Glfw({})) == []
    assert placement.screens(object()) == []                   # a window system that will not say
    # with no screens there is nothing to place on: the size comes back, no note
    assert place("render", RENDER, [], 1, entry(1, 2, 3, 4)) == ((16, 16, 1280, 820), "")


def test_placement_imports_nothing_from_the_package():
    """No GL, no imgui, nothing from hyperspace: glfw is passed in (the
    rule tests/test_lfo_boundary.py holds for the clock and the LFOs)."""
    tree = ast.parse(Path(placement.__file__).read_text())
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom):
            assert not n.level, f"placement.py imports from the package: {'.' * n.level}{n.module}"
            mods = [n.module or ""]
        elif isinstance(n, ast.Import):
            mods = [a.name for a in n.names]
        else:
            continue
        for mod in mods:
            root = mod.split(".")[0]
            assert root not in {"hyperspace", "glfw", "moderngl", "imgui_bundle"}, mod
