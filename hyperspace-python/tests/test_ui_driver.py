"""tests/ui_driver.py on the real panel: the VIEW page's instance controls
set by the mouse and the keys, through imgui's own input queue — the count
typed in, Fit clicked, a lattice picked from the Layout menu, the field's
depth dragged and typed — each control found by its param id."""

import pytest
from imgui_bundle import imgui
from test_ui_shell import build_rig, frame
from ui_driver import Driver

from hyperspace.field import NAMES


@pytest.fixture()
def view_page(tmp_path, monkeypatch):
    with build_rig(tmp_path) as r:
        # the real route: the VIEW section focused in the pane, the window
        # tall enough to hold the whole of it
        r.panel.desk = False
        imgui.get_io().display_size = imgui.ImVec2(1600, 2000)
        d = Driver(step=lambda: frame(r.panel, "view"))
        d.record(monkeypatch.setattr)
        d.run(d.wait(2))
        yield r, d


def test_the_instance_controls_answer_the_mouse_and_the_keys(view_page):
    r, d = view_page
    v, reg = r.view, r.reg
    d.run(d.enter("view.instances", 12))                 # Ctrl+click, type, Enter
    assert v.instances == 12
    assert not v.inst_fit
    d.run(d.click("view.inst_fit"), d.park())
    assert v.inst_fit
    d.run(d.pick("view.inst_layout", NAMES.index("FCC")))
    assert NAMES[v.inst_layout] == "FCC"
    d.run(d.wait(1))                                     # the lattice's depth slider appears
    d.run(d.slide("view.inst_persp", 1.0), d.park())
    assert v.inst_persp > 0.9
    d.run(d.enter("view.inst_persp", 0.25))
    assert v.inst_persp == pytest.approx(0.25)
    d.run(d.pick("view.inst_layout", NAMES.index("GRID")))
    assert v.inst_layout == 0
    d.run(d.click("view.inst_fit"), d.park())
    assert not v.inst_fit
    assert reg["view.instances"].value == 12             # nothing else moved


@pytest.mark.parametrize("mac", [False, True], ids=["ctrl", "cmd"])
def test_a_value_is_typed_in_under_either_modifier(view_page, mac):
    """imgui swaps Ctrl and Cmd as they enter its queue under
    `config_mac_osx_behaviors`, on by default on a Mac: the driver's Ctrl
    is whichever key imgui reads as Ctrl, so a value is typed in on both
    platforms — here under each setting, whatever the machine."""
    r, d = view_page
    imgui.get_io().config_mac_osx_behaviors = mac
    d.run(d.enter("view.instances", 7))
    assert r.view.instances == 7


def test_a_control_not_drawn_is_named_in_the_error(view_page):
    r, d = view_page
    r.view.instances = 1                                 # one copy: no field rows
    d.run(d.wait(2))
    with pytest.raises(KeyError, match="view.inst_persp"):
        d.rect("view.inst_persp")


def test_a_control_that_went_away_is_not_found_where_it_was(view_page):
    """A control drawn once and then no longer (a lattice's depth, gone
    with the lattice) is missing, not found at its old place — where
    another control may be drawn now."""
    r, d = view_page
    r.view.instances, r.view.inst_layout = 12, NAMES.index("FCC")
    d.run(d.wait(2))
    assert d.rect("view.inst_persp")
    r.view.inst_layout = NAMES.index("GRID")              # the depth slider goes
    d.run(d.wait(2))
    with pytest.raises(KeyError, match="view.inst_persp"):
        d.rect("view.inst_persp")
    assert d.rect("view.inst_spacing")                    # what is drawn still is
