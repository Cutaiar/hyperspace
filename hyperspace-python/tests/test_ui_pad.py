# ruff: noqa: F811 — `rig` is test_ui_shell's fixture, taken as each test's argument
"""The gamepad drawn on screen (ui_pad.py), the desk's picture for the pad.

The layout (`gamepad.LAYOUT`): one entry per control a row can name, none
overlapping, a unique glyph each. The diagram: what it lights is the
table's pad rows, with the app's own hand on a free axis lit grey beside
them; the live pad shows through it; the desk keeps clear of it. Headless
imgui, a library on tmp_path — no pad is plugged in anywhere here.
"""

import pytest
from imgui_bundle import imgui
from test_ui_shell import (
    NARROW_CONTROL,
    frame,
    rig,  # noqa: F401 — the headless panel fixture
)

from hyperspace import apc40, gamepad, ui_desk, ui_pad
from hyperspace.app import CONTROL_SIZE
from hyperspace.routing import Binding, padmap

# ---------------------------------------------------------------- the layout


def test_one_layout_entry_per_control_the_pad_sends():
    """Every button, D-pad direction and axis gamepad.py names is on the
    layout, once, with a name in words and a kind the diagram draws."""
    srcs = [c.source for c in gamepad.LAYOUT]
    want = ({f"pad:{n}" for n in gamepad.BUTTONS} | {f"hat:{n}" for n in gamepad.HATS}
            | {f"axis:{n}" for n in gamepad.AXES})
    assert len(srcs) == len(set(srcs)) and set(srcs) == want
    for c in gamepad.LAYOUT:
        assert c.kind in ("button", "stick", "axis"), c
        assert gamepad.control_name(c.source) == c.name and c.name != c.source, c


def test_no_two_layout_entries_overlap():
    cs = gamepad.LAYOUT
    for i, a in enumerate(cs):
        assert a.w > 0 and a.h > 0 and a.x >= 0 and a.y >= 0, a
        for b in cs[i + 1:]:
            apart = (a.x + a.w <= b.x or b.x + b.w <= a.x
                     or a.y + a.h <= b.y or b.y + b.h <= a.y)
            assert apart, f"{a} overlaps {b}"


def test_glyphs_are_unique_and_short():
    gs = [c.glyph for c in gamepad.LAYOUT]
    assert len(set(gs)) == len(gs) and max(map(len, gs)) <= 5
    assert {"A", "B", "X", "Y", "LB", "RB", "LS", "RS"} <= set(gs)
    assert {"↑", "↓", "←", "→"} <= set(gs) and set(gamepad.AXES) <= set(gs)


def test_a_lane_addressed_by_number_names_the_same_control():
    """An older file's `axis:4` is the left trigger, as `axis:LT` is."""
    assert gamepad.control("axis:4") is gamepad.control("axis:LT")
    assert gamepad.glyph("axis:4") == "LT" and gamepad.named("pad:LB") == "LB (left bumper)"
    for bad in ("cc:0:48", "key:H", "hand:left.x", "axis:ZZ", "pad:NOPE", "axis:99"):
        assert gamepad.control(bad) is None and gamepad.glyph(bad) is None


# ---------------------------------------------------------------- what it lights


def test_every_factory_pad_row_lands_on_a_control(rig):
    """`rows` reads the table's pad, D-pad and axis rows — the factory
    map's thirteen, each on the control it names."""
    table = rig.router.table
    got = ui_pad.rows(table)
    assert set(got) == {b.source for b in padmap()}
    assert all(got[s].source == s for s in got)
    assert all(gamepad.control(s) is not None for s in got)


def test_a_disabled_row_does_not_light(rig):
    table = rig.router.table
    row = next(b for b in table.bindings if b.source == "pad:A")
    assert "pad:A" in ui_pad.rows(table)
    row.enabled = False
    assert "pad:A" not in ui_pad.rows(table)


def test_a_free_axis_says_what_the_app_does_with_it(rig):
    """No route on an axis: the lane is lit with the app's own words
    (`BUILT_IN`) and no row; a route on it takes the words over."""
    panel, table = rig.panel, rig.router.table
    lx = next(c for c in gamepad.LAYOUT if c.source == "axis:LX")
    assert ui_pad.rows(table).get("axis:LX") is None
    assert ui_pad.says(panel, lx, None) == "Orbit yaw"
    table.add(Binding("axis:LX", "view.bright", "push", 0.5))
    b = ui_pad.rows(table)["axis:LX"]
    assert ui_pad.says(panel, lx, b) == panel.reg["view.bright"].label


def test_a_control_with_nothing_on_it_is_dark(rig):
    panel = rig.panel
    share = next(c for c in gamepad.LAYOUT if c.source == "pad:SHARE")
    assert ui_pad.says(panel, share, None) == ""
    assert "free" in ui_pad.label(panel, share, None)


def test_the_hover_names_glyph_param_and_source(rig):
    panel, table = rig.panel, rig.router.table
    lb = next(c for c in gamepad.LAYOUT if c.source == "pad:LB")
    tip = ui_pad.label(panel, lb, ui_pad.rows(table)["pad:LB"])
    assert tip.startswith("LB · view.shape · ")
    assert "left bumper" in tip and "Learn pad" in tip


# ---------------------------------------------------------------- the room


def test_the_pad_takes_the_top_of_the_desks_column():
    """`room`: top-left, left of the panel, never over `MAX_H` of the
    display; the desk, which grows up from the foot of the same column,
    starts under it (`ui_desk.room`'s `pad_h`)."""
    display = tuple(float(v) for v in NARROW_CONTROL)             # 960 × 900
    panel_x = display[0] - 540 - 12
    E = ui_pad.EDGE
    x, y, w, h = ui_pad.room(display, panel_x)
    assert (x, y) == (E, E) and x + w <= panel_x - E
    assert h <= ui_pad.MAX_H * display[1]
    # the panel hidden: wider, and wide enough for the labels
    _, _, w2, h2 = ui_pad.room(display, None)
    assert w2 > w and (w2 - 2 * ui_pad.PAD) / gamepad.LAYOUT_W >= ui_pad.LABEL_UNIT
    # a panel dragged far left: never narrower than MIN_W
    assert ui_pad.room(display, 100.0)[2] == ui_pad.MIN_W
    # the desk under it: its top edge clears the pad and the gap. With the
    # panel open the desk is already shorter than its column (a unit is
    # never taller than it is wide), so only the hidden-panel desk, which
    # takes every pixel it is given, is pushed down by the pad over it
    dy = ui_desk.room(display, None, None, h2)[1]
    assert dy >= E + h2 + ui_desk.GAP
    assert dy > ui_desk.room(display, None, None)[1]
    assert ui_desk.room(display, panel_x, None, h)[3] == ui_desk.room(display, panel_x, None)[3]


def test_a_unit_is_never_taller_than_it_is_wide():
    for display in ((960.0, 900.0), (1512.0, 900.0), (2560.0, 1440.0), (1600.0, 400.0)):
        _, _, w, h = ui_pad.room(display, None)
        sx = (w - 2 * ui_pad.PAD) / gamepad.LAYOUT_W
        sy = (h - 2 * ui_pad.PAD - ui_pad.HEAD_H) / gamepad.LAYOUT_H
        assert sy <= sx + 1e-6, (display, sx, sy)


# ---------------------------------------------------------------- the drawing


class _Ink:
    """The window's draw list, recording the text drawn through it."""

    def __init__(self, dl, texts):
        self._dl, self._texts = dl, texts

    def add_text(self, pos, col, text):
        self._texts.append(text)
        return self._dl.add_text(pos, col, text)

    def __getattr__(self, name):
        return getattr(self._dl, name)


def _pad_frames(rig, monkeypatch, n=3) -> dict:
    """Draw `n` frames and return what the pad window was and drew on the
    last: its rect, its scroll range, the text on its draw list, and a
    readout's `Ctx` (its reading and hit areas) where one drew."""
    from hyperspace import ui_pad_views
    out: dict = {"texts": [], "rect": None, "ctx": None}
    real_body, real_dl = ui_pad._body, imgui.get_window_draw_list
    real_draw = ui_pad_views.draw

    def draw(*a, **k):
        out["ctx"] = real_draw(*a, **k)
        return out["ctx"]
    monkeypatch.setattr(ui_pad_views, "draw", draw)

    def body(p, table):
        out["texts"].clear()
        pos, size = imgui.get_window_pos(), imgui.get_window_size()
        with monkeypatch.context() as m:
            m.setattr(imgui, "get_window_draw_list", lambda: _Ink(real_dl(), out["texts"]))
            real_body(p, table)
        out["rect"] = (pos.x, pos.y, size.x, size.y)
        out["scroll"] = (imgui.get_scroll_max_x(), imgui.get_scroll_max_y())
    monkeypatch.setattr(ui_pad, "_body", body)
    for _ in range(n):
        frame(rig.panel)
    monkeypatch.setattr(ui_pad, "_body", real_body)
    monkeypatch.setattr(ui_pad_views, "draw", real_draw)
    return out


def test_the_switch_draws_it_and_hides_it(rig, monkeypatch):
    """`ui.pad_diagram`: off at launch — nothing is drawn and the desk
    keeps the whole column — on, the window is there."""
    panel, reg = rig.panel, rig.reg
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
    assert reg["ui.pad_diagram"].value is False
    assert _pad_frames(rig, monkeypatch)["rect"] is None
    assert panel._pad_h == 0.0
    reg["ui.pad_diagram"].set(True)
    got = _pad_frames(rig, monkeypatch)
    assert got["rect"] is not None and got["rect"][:2] == (ui_pad.EDGE, ui_pad.EDGE)
    assert panel._pad_h == got["rect"][3]


def test_the_big_pad_names_every_lit_control_and_never_scrolls(rig, monkeypatch):
    """Panel hidden at the control size: a label is drawn for each lit
    control — the table's rows and the free axes' built-in words — and
    none for a dark one; the window has no scroll range."""
    panel, reg = rig.panel, rig.reg
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
    reg["ui.pad_diagram"].set(True)
    reg["ui.panel"].set(False)
    got = _pad_frames(rig, monkeypatch)
    mapped = ui_pad.rows(rig.router.table)
    lit = set(mapped) | set(ui_pad.BUILT_IN)
    labels = ui_pad._state(panel)["labels"]
    assert len(labels) == len(lit)
    assert set(ui_pad.BUILT_IN.values()) <= set(labels)
    assert got["scroll"] == (0.0, 0.0)
    # every glyph is drawn, dark controls included; a dark one has no label
    assert {c.glyph for c in gamepad.LAYOUT} <= set(got["texts"])
    assert panel.reg["view.shape"].label in " ".join(labels)       # LB / RB's row


def test_the_small_pad_draws_glyphs_only(rig, monkeypatch):
    """The panel open, the pad beside it: the units are too small for
    labels, so the picture is the glyphs."""
    panel, reg = rig.panel, rig.reg
    imgui.get_io().display_size = imgui.ImVec2(*NARROW_CONTROL)
    reg["ui.pad_diagram"].set(True)
    got = _pad_frames(rig, monkeypatch)
    assert ui_pad._state(panel)["unit"][0] < ui_pad.LABEL_UNIT
    assert ui_pad._state(panel)["labels"] == []
    assert set(got["texts"]) == {c.glyph for c in gamepad.LAYOUT}


def test_the_desk_moves_under_the_pad(rig, monkeypatch):
    """Both up with the panel hidden: the desk is drawn under the pad,
    not over it."""
    reg = rig.reg
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
    reg["ui.pad_diagram"].set(True)
    reg["ui.panel"].set(False)
    pad_rect = _pad_frames(rig, monkeypatch)["rect"]
    desk = ui_desk._room(rig.panel)
    assert desk[1] >= pad_rect[1] + pad_rect[3] + ui_desk.GAP
    assert desk[1] + desk[3] <= CONTROL_SIZE[1] - ui_desk.EDGE
    assert {c.glyph for c in apc40.LAYOUT}      # the desk still has its own picture


# ---------------------------------------------------------------- the live pad


class _FakePad:
    """A pad the way `gamepad.Pad` is read: buttons down, a hat mask, the
    six lanes. Nothing here touches GLFW."""

    def __init__(self, down=(), hat=0, lanes=None):
        self.on = True
        self.source = "glfw"
        self._down = {gamepad.BUTTONS[n] for n in down}
        self.hat = hat
        self._lanes = list(lanes if lanes is not None else gamepad.AXIS_RESTS)

    def down(self, b: int) -> bool:
        return b in self._down

    def lanes(self) -> list[float]:
        return self._lanes


def test_the_live_pad_shows_through_the_picture(rig):
    panel = rig.panel
    a = next(c for c in gamepad.LAYOUT if c.source == "pad:A")
    up = next(c for c in gamepad.LAYOUT if c.source == "hat:UP")
    ls = next(c for c in gamepad.LAYOUT if c.source == "pad:LSTICK")
    assert not ui_pad.held(None, a)                      # no pad: nothing is held
    assert ui_pad._stick(None, ls) == (0.0, 0.0)
    panel.pad = _FakePad(down=("A",), hat=gamepad.HAT_UP, lanes=[1.0, 1.0, 0.5, 0.5, 0.0, 0.7])
    assert ui_pad.held(panel.pad, a) and ui_pad.held(panel.pad, up)
    assert not ui_pad.held(panel.pad, next(c for c in gamepad.LAYOUT if c.source == "pad:B"))
    assert ui_pad.lane(panel.pad, "RT") == 0.7
    assert ui_pad._stick(panel.pad, ls) == (1.0, -1.0)   # right and up, y down on screen


def test_the_header_says_how_the_pad_is_read(rig):
    panel = rig.panel
    panel.pad = None
    assert ui_pad.state(panel)[0] == "off"
    panel.pad = _FakePad()
    assert ui_pad.state(panel)[0] == "on"
    panel.pad.source = "usb"
    assert ui_pad.state(panel)[0] == "over USB"
    panel.pad.source, panel.pad.on = None, False
    assert ui_pad.state(panel)[0] == "no pad"


def test_it_draws_with_a_pad_on_it(rig, monkeypatch):
    """The same picture, a live pad under it: held buttons and pushed
    sticks change no label and raise nothing."""
    reg = rig.reg
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
    reg["ui.pad_diagram"].set(True)
    reg["ui.panel"].set(False)
    before = _pad_frames(rig, monkeypatch)["texts"]
    rig.panel.pad = _FakePad(down=("A", "LB", "LSTICK"), hat=gamepad.HAT_LEFT,
                             lanes=[0.9, 0.1, 0.5, 0.5, 1.0, 0.0])
    assert _pad_frames(rig, monkeypatch)["texts"] == before


# ---- a pad's own face (plan 42) ----

def test_the_edge_draws_its_own_face_and_its_extras_without_overlap():
    from hyperspace.pads import models
    edge = gamepad.layout_for(models.MODELS["edge"])
    assert gamepad.layout_for(None) is gamepad.LAYOUT
    assert gamepad.layout_for(models.MODELS["xbox"]) == gamepad.LAYOUT
    glyphs = {c.source: c.glyph for c in edge}
    assert glyphs["pad:A"] == "✕" and glyphs["pad:Y"] == "△" and glyphs["axis:LT"] == "L2"
    assert {"pad:TOUCH", "motion:roll", "pad:LP", "pad:RP", "pad:LFN", "pad:RFN"} <= set(glyphs)
    assert len(set(glyphs.values())) == len(glyphs)
    for i, a in enumerate(edge):
        assert a.x + a.w <= gamepad.LAYOUT_W + 1e-9 and a.y + a.h <= gamepad.LAYOUT_H + 1e-9
        for b in edge[i + 1:]:
            apart = (a.x + a.w <= b.x or b.x + b.w <= a.x or a.y + a.h <= b.y or b.y + b.h <= a.y)
            assert apart, (a.source, b.source)
    ds = {c.source for c in gamepad.layout_for(models.MODELS["dualsense"])}
    assert "pad:TOUCH" in ds and "pad:LP" not in ds          # no back buttons on a DualSense


def test_touch_and_motion_rows_light_the_touchpad_and_the_tilt():
    edge = gamepad.layout_for(gamepad.models.MODELS["edge"])
    assert gamepad.control_in(edge, "touch:pinch").kind == "touchpad"
    assert gamepad.control_in(edge, "motion:shake").kind == "tilt"
    assert gamepad.control_in(edge, "pad:A").glyph == "✕"
    from types import SimpleNamespace as NS
    table = NS(of=lambda *s: [Binding("touch:x", "fx.zoomblur.cx", "position"),
                              Binding("motion:roll", "rot.phase.XY", "push", 0.25)])
    got = ui_pad.rows(table)
    assert set(got) == {"pad:TOUCH", "motion:roll"}


def test_each_stick_well_shows_its_own_stick_on_a_sony_face():
    """The well picks its axes by the control, not the glyph (an Edge's
    left stick is "L3", not "LS": both wells once read the right stick)."""
    from types import SimpleNamespace as NS
    edge = gamepad.layout_for(gamepad.models.MODELS["edge"])
    ls = next(c for c in edge if c.source == "pad:LSTICK")
    rs = next(c for c in edge if c.source == "pad:RSTICK")
    pad = NS(lanes=lambda: [1.0, 0.5, 0.5, 1.0, 0.0, 0.0])    # left stick right, right stick up
    assert ui_pad._stick(pad, ls) == (1.0, 0.0) and ui_pad._stick(pad, rs) == (0.0, -1.0)


# ---- the readouts (plan 42's follow-up): map, faithful, lanes, cockpit ----

def _edge_pad():
    """An Edge read from the real Bluetooth bytes (tests/fixtures/pads),
    polled long enough for its tilt to settle."""
    from pathlib import Path
    tape = Path(__file__).resolve().parent / "fixtures" / "pads" / "edge-bt-excerpt.jsonl"
    pad = gamepad.Pad(tape=str(tape))
    for _ in range(30):
        pad.poll(1 / 60)
    return pad


def test_every_view_draws_every_pad_and_never_scrolls(rig, monkeypatch):
    """Each view at the control size, the panel hidden and shown: no pad,
    an Xbox pad, a real Edge — drawn in the map's own room (the desk under
    it never moves) and never scrolling. (Headless, Faithful and Cockpit
    are the room's note that NanoVG cannot draw here; their drawings are
    the tests below, through the hit pen and a stand-in NanoVG.)"""
    from hyperspace import ui_pad_views
    reg = rig.reg
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
    reg["ui.pad_diagram"].set(True)
    pads = {"none": None, "xbox": _FakePad(down=("A",), lanes=[0.9, 0.1, 0.5, 0.5, 1.0, 0.0]),
            "edge": _edge_pad()}
    for panel_on in (False, True):
        reg["ui.panel"].set(panel_on)
        rig.panel.pad = None
        reg["ui.pad_view"].set(0)
        room = _pad_frames(rig, monkeypatch)["rect"]
        for k, view in enumerate(ui_pad_views.VIEWS):
            reg["ui.pad_view"].set(k)
            for name, pad in pads.items():
                rig.panel.pad = pad
                got = _pad_frames(rig, monkeypatch)
                assert got["rect"] == room, (view, name)
                assert got["scroll"] == (0.0, 0.0), (view, name)
                assert ui_pad.view_of(rig.panel) == view


def test_the_header_steps_through_the_views():
    from types import SimpleNamespace as NS
    panel = NS(pad_view=0)
    seen = []
    for _ in range(5):
        seen.append(ui_pad.view_of(panel))
        ui_pad.step_view(panel)
    assert seen == ["map", "faithful", "lanes", "cockpit", "map"]
    panel.pad_view = 9                                     # out of range: the map
    assert ui_pad.view_of(panel) == "map"


def test_the_edge_views_show_what_it_has_and_what_maps_it(rig, monkeypatch):
    """Faithful and cockpit place the Edge's back and Fn buttons and its
    touchpad where a hover finds them; the lanes name every touch and
    motion lane and say a touch row's mapping."""
    from hyperspace import ui_pad_views
    reg = rig.reg
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
    reg["ui.pad_diagram"].set(True)
    reg["ui.panel"].set(False)
    rig.router.table.add(Binding("touch:pinch", "camera.zoom", "push", 0.5))
    rig.panel.pad = _edge_pad()
    reg["ui.pad_view"].set(ui_pad_views.VIEWS.index("lanes"))
    ctx = _pad_frames(rig, monkeypatch)["ctx"]
    assert ctx.r.on and ctx.r.model.id == "edge" and ctx.r.touch is not None
    assert {"touch:pinch", "motion:shake", "pad:LP"} <= {h[4] for h in ctx.hits}
    assert {"pad:LP", "pad:RP", "pad:LFN", "pad:TOUCH"} <= {
        h[4] for h in _drawn("faithful", rig.panel.pad)}
    assert {"pad:LP", "pad:RP", "pad:TOUCH", "axis:LT", "axis:RT"} <= {
        h[4] for h in _drawn("cockpit", rig.panel.pad)}
    says = ui_pad._says_of(rig.panel, rig.router.table)
    words, row = says("touch:pinch")
    assert row is not None and words
    assert says("axis:LX") == (ui_pad.BUILT_IN["axis:LX"], None)


def test_a_reading_of_no_pad_and_of_a_pad_without_extras():
    from hyperspace import ui_pad_views
    r = ui_pad_views.read(None)
    assert not r.on and r.touch is None and r.axes["LX"] == 0.5
    fake = _FakePad(down=("B",), hat=gamepad.HAT_UP)
    r = ui_pad_views.read(fake)
    assert r.on and r.down == {"B"} and r.hat == gamepad.HAT_UP and r.motion is None
    assert not r.has("touch") and r.effects is None


# ---- Faithful and Cockpit drawn the lab's way (ui_pad_lab) ----

def _drawn(view, pad, st=None):
    """`view` drawn by ui_pad_lab with a pen that keeps only its hits (no
    GPU): the hits, in the lab's 1000 × 620 design space."""
    from hyperspace import ui_pad_lab, ui_pad_views
    pen = ui_pad_lab.Pen()
    ui_pad_lab.VIEWS[view](pen, ui_pad_views.read(pad), {} if st is None else st)
    return pen.hits


def test_the_lab_drawings_place_every_control_inside_the_design_space():
    """Every pad in both lab views: each control has a hit area inside the
    design space; an Edge shows its back and Fn buttons and touchpad, an
    Xbox pad and no pad only what they have."""
    from hyperspace import ui_pad_lab
    pads = {"none": None, "xbox": _FakePad(down=("A",), lanes=[0.9, 0.1, 0.5, 0.5, 1.0, 0.0]),
            "edge": _edge_pad()}
    for view in ui_pad_lab.VIEWS:
        for name, pad in pads.items():
            hits = _drawn(view, pad)
            for x, y, w, h, source in hits:
                assert 0 <= x and x + w <= ui_pad_lab.DESIGN_W, (view, name, source)
                assert 0 <= y and y + h <= ui_pad_lab.DESIGN_H, (view, name, source)
            got = {h[4] for h in hits}
            assert {"pad:A", "pad:B", "pad:X", "pad:Y", "pad:LSTICK", "pad:RSTICK", "hat:UP",
                    "axis:LT", "axis:RT", "pad:LB", "pad:RB", "pad:GUIDE"} <= got, (view, name)
            extras = {"pad:LP", "pad:RP", "pad:LFN", "pad:RFN", "pad:TOUCH"}
            if name == "edge":
                assert extras <= got, (view, got)
            else:
                assert not extras & got, (view, name, got)


def test_the_cockpit_keeps_a_trail_and_a_ticker_on_the_panel():
    """The cockpit's memory is the state it is handed (kept on the panel):
    a stick trail per side, capped, and a press on the ticker once."""
    from hyperspace import ui_pad_lab
    st = {}
    pad = _FakePad(down=("A",))
    for _ in range(ui_pad_lab.TRAIL + 10):
        _drawn("cockpit", pad, st)
    assert {len(t) for t in st["trails"].values()} == {ui_pad_lab.TRAIL}
    assert [k for k, _t in st["events"]] == ["pad:A"]


def test_the_horizon_is_cut_to_its_ring():
    """The pen cannot clip to a circle, so the tilt's lines are cut to it."""
    from hyperspace import ui_pad_lab
    a, b = ui_pad_lab._clip((-20, 0), (20, 0), 0, 0, 10)
    assert a == (-10, 0) and b == (10, 0)
    assert ui_pad_lab._clip((-5, 0), (5, 0), 0, 0, 10) == ((-5, 0), (5, 0))
    assert ui_pad_lab._clip((-20, 15), (20, 15), 0, 0, 10) is None


def test_where_nanovg_cannot_draw_the_room_says_why(rig, monkeypatch):
    """The headless panel has no GL: NanoVG is not started (nor marked
    failed), nothing else draws Faithful or Cockpit, and the room says why
    and that Map and Lanes still work; with NanoVG kept off, it says that."""
    from hyperspace import ui_pad_nvg, ui_pad_views
    reg = rig.reg
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
    reg["ui.pad_diagram"].set(True)
    reg["ui.panel"].set(False)
    rig.panel.pad = _edge_pad()
    for view in ("faithful", "cockpit"):
        reg["ui.pad_view"].set(ui_pad_views.VIEWS.index(view))
        got = _pad_frames(rig, monkeypatch)
        texts = got["texts"]
        name = ui_pad_views.VIEW_LABELS[ui_pad_views.VIEWS.index(view)]
        assert f"{name} is drawn with NanoVG." in texts, texts
        assert "no OpenGL here for NanoVG" in texts and "Map and Lanes still work." in texts
        assert not got["ctx"].hits                               # nothing to hover
    surf = ui_pad_nvg.surface_of(rig.panel)
    assert surf.vg is None and not surf.failed
    monkeypatch.setenv("HYPERSPACE_NANOVG", "0")
    assert "NanoVG is off (HYPERSPACE_NANOVG=0)" in _pad_frames(rig, monkeypatch)["texts"]


def test_the_lab_colours_read_every_way_the_port_writes_them():
    from hyperspace import ui_pad_lab
    assert ui_pad_lab.rgba("#000") == (0.0, 0.0, 0.0, 1.0)
    assert ui_pad_lab.rgba("hot") == ui_pad_lab.rgba(ui_pad_lab.COL["hot"])
    assert ui_pad_lab.rgba((255, 0, 128), 0.5) == (1.0, 0.0, 128 / 255, 0.5)


class _Nvg:
    """A stand-in for imgui-bundle's nanovg module: any call (recorded by
    name), any enum (its `.value` 0). Every name reached from the module
    is kept in `paths`, to check against the real module (a misspelt call
    would pass here and fail in the app); a call's result is no module's."""

    def __init__(self, calls, name="nvg", path="", paths=None):
        self._calls, self._name, self._path = calls, name, path
        self.paths = paths if paths is not None else set()

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        if name == "value":
            return 0
        path = None if self._path is None else f"{self._path}.{name}".lstrip(".")
        if path is not None:
            self.paths.add(path)
        return _Nvg(self._calls, name, path, self.paths)

    def __call__(self, *args, **kwargs):
        self._calls.append(self._name)
        return _Nvg(self._calls, "result", None, self.paths)


def test_the_nanovg_pen_draws_every_call_the_drawings_make():
    """Both drawings, every pad, through the NanoVG pen: it makes every one
    of the pen's drawing calls itself (none falls to the base, which draws
    nothing), they reach NanoVG, and the hits are the base pen's own."""
    from hyperspace import ui_pad_lab, ui_pad_nvg, ui_pad_views
    assert set(ui_pad_lab.DRAW_CALLS) <= set(vars(ui_pad_nvg.NvgPen))
    from imgui_bundle import nanovg as real
    pads = {"none": None, "xbox": _FakePad(down=("A",)), "edge": _edge_pad()}
    used: set[str] = set()
    for view in ui_pad_lab.VIEWS:
        for name, pad in pads.items():
            calls: list[str] = []
            stand_in = _Nvg(calls)
            pen = ui_pad_nvg.NvgPen(object(), stand_in)
            r = ui_pad_views.read(pad)
            ui_pad_lab.VIEWS[view](pen, r, {})
            assert {"begin_path", "fill", "stroke", "text"} <= set(calls), (view, name)
            hits = ui_pad_lab.Pen()
            ui_pad_lab.VIEWS[view](hits, r, {})
            assert {h[4] for h in pen.hits} == {h[4] for h in hits.hits}, (view, name)
            used |= stand_in.paths
    for path in sorted(used):                   # every name the pen reached is NanoVG's own
        obj = real
        for part in path.split("."):
            assert hasattr(obj, part), path
            obj = getattr(obj, part)
    for view, want in (("faithful", {"bezier_to", "quad_to", "rounded_rect"}),   # body, light bar
                       ("cockpit", {"arc", "circle"})):                           # the dials
        calls = []
        ui_pad_lab.VIEWS[view](ui_pad_nvg.NvgPen(object(), _Nvg(calls)),
                               ui_pad_views.read(_edge_pad()), {})
        assert want <= set(calls), view


def test_nanovg_waits_for_gl_and_can_be_kept_off(monkeypatch, capsys):
    """No GL context: not started and not failed (it may start later), and
    nothing said yet. HYPERSPACE_NANOVG=0: never started, GL not even
    asked, and the terminal told once why."""
    from hyperspace import ui_pad_nvg
    surf = ui_pad_nvg.Surface()
    monkeypatch.setattr(ui_pad_nvg, "_gl_current", lambda: False)
    assert not surf.ready() and not surf.failed and surf.vg is None
    assert "pad drawings" not in capsys.readouterr().err

    def asked():
        raise AssertionError("GL asked with NanoVG kept off")
    monkeypatch.setattr(ui_pad_nvg, "_gl_current", asked)
    monkeypatch.setenv("HYPERSPACE_NANOVG", "0")
    assert not surf.ready() and not surf.failed
    assert not surf.ready()
    assert capsys.readouterr().err.count("pad drawings: off (HYPERSPACE_NANOVG=0)") == 1


def test_each_room_keeps_its_own_framebuffer():
    """The pad window and GRAPH's side panel draw at their own sizes: each
    keeps its framebuffer (none remade while its size holds — remade twice
    a frame, the frame rate fell), and a room no longer drawn lets its
    framebuffer go."""
    from hyperspace import ui_pad_nvg, ui_pad_views
    calls: list[str] = []
    surf = ui_pad_nvg.Surface()
    surf.vg, surf.nvg = object(), _Nvg(calls)
    r = ui_pad_views.read(None)
    for k in range(5):
        surf.render("faithful", r, {}, 800, 500, "window", k)
        surf.render("cockpit", r, {}, 300, 200, "side", k)
    assert calls.count("NvgFramebuffer") == 2 and set(surf.fbs) == {"window", "side"}
    surf.render("faithful", r, {}, 820, 500, "window", 6)          # resized: remade once
    assert calls.count("NvgFramebuffer") == 3
    surf.render("faithful", r, {}, 820, 500, "window", 7 + ui_pad_nvg.STALE)
    assert set(surf.fbs) == {"window"}                              # the side panel's went


# ---- the review of 2026-11-02 (deep review and Devin's): each finding's test ----

def _side_frame(panel, monkeypatch, width: float) -> list[str]:
    """GRAPH's side panel as wide as `width`: the pad picture drawn there
    (ui_pad.inline), the text it put on the draw list back."""
    texts: list[str] = []
    real_dl = imgui.get_window_draw_list
    imgui.new_frame()
    imgui.set_next_window_size(imgui.ImVec2(width, 900))
    imgui.begin("side")
    with monkeypatch.context() as m:
        m.setattr(imgui, "get_window_draw_list", lambda: _Ink(real_dl(), texts))
        ui_pad.inline(panel)
    imgui.end()
    imgui.end_frame()
    return texts


def test_lanes_stay_readable_in_graphs_side_panel(rig, monkeypatch):
    """GRAPH's side panel at its narrowest: Lanes keeps its columns wide
    enough to read — each lane's address whole, not "ax…" — taking the
    height that needs (the side panel scrolls)."""
    from hyperspace import ui_graph, ui_pad_views
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
    rig.panel.pad = _edge_pad()
    rig.reg["ui.pad_view"].set(ui_pad_views.VIEWS.index("lanes"))
    texts = _side_frame(rig.panel, monkeypatch, ui_graph.SIDE_MIN)
    for name in ("axis:LX", "axis:RT", "hat:UP", "pad:A", "touch:pinch", "motion:roll"):
        assert name in texts, (name, [t for t in texts if t.endswith("…")][:8])


def test_closing_the_panel_lets_nanovg_go(rig):
    """Panel.close (on quit and ⌘R, while the control window's GL is
    still up) frees NanoVG's framebuffers and its context — not the
    interpreter's exit, after GLFW has gone."""
    from hyperspace import ui_pad_nvg
    calls: list[str] = []
    surf = ui_pad_nvg.surface_of(rig.panel)
    surf.vg, surf.nvg = object(), _Nvg(calls)
    surf.fbs["room"] = [object(), (1, 1), 0]
    rig.panel.close()
    assert not surf.fbs and surf.vg is None
    assert "delete_nvg_context_hello_imgui" in calls
    rig.panel.close()                                          # twice: nothing more


def test_a_routed_dial_lane_shows_in_lanes(rig, monkeypatch):
    """A row on one of a stick's direction lanes (``axis:L.N``) shows in
    Lanes with its value and mapping; the unrouted ones stay out."""
    from hyperspace import ui_pad_views
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
    reg = rig.reg
    reg["ui.pad_diagram"].set(True)
    reg["ui.panel"].set(False)
    rig.router.table.add(Binding("axis:L.N", "camera.zoom", "position"))
    lanes = list(gamepad.LANE_RESTS)
    lanes[gamepad.LANES.index("L.N")] = 0.8
    rig.panel.pad = _FakePad(lanes=lanes)
    reg["ui.pad_view"].set(ui_pad_views.VIEWS.index("lanes"))
    texts = _pad_frames(rig, monkeypatch)["texts"]
    assert "axis:L.N" in texts and "0.80" in texts
    assert "axis:R.S" not in texts


def test_a_disabled_or_replaced_row_stops_showing_at_once(rig):
    """Rows are edited in place — disabled (the ROUTING page's checkbox,
    `Bindings.enable`), re-pointed (`move_route`) — and the readouts and
    the map show it on the next frame, from the table's serial: the cache
    key never scans the rows (the pad window reads it every frame)."""
    table = rig.router.table
    assert not [r for r in table.of("pad") if r.source in ("pad:RFN", "pad:LFN")]   # free
    b = table.add(Binding("pad:RFN", "camera.zoom", "push", 0.5))
    assert ui_pad._says_of(rig.panel, table)("pad:RFN")[1] is b
    assert ui_pad.rows_cached(rig.panel, table)["pad:RFN"] is b
    table.enable(b, False)
    assert ui_pad._says_of(rig.panel, table)("pad:RFN")[1] is None
    assert "pad:RFN" not in ui_pad.rows_cached(rig.panel, table)
    table.enable(b, True)
    table.move_route(b, source="pad:LFN")
    assert ui_pad._says_of(rig.panel, table)("pad:LFN")[1] is b
    assert "pad:RFN" not in ui_pad.rows_cached(rig.panel, table)
    seen = []
    real_of = table.of
    table.of = lambda *s: (seen.append(s), real_of(*s))[1]
    ui_pad._says_of(rig.panel, table)
    ui_pad.rows_cached(rig.panel, table)
    del table.of
    assert not seen                                     # nothing changed: no scan of the rows


def test_a_sticks_hover_names_both_its_axes_and_its_click():
    """Hovering a stick names what its X and Y axes and its click do —
    in Faithful and in Cockpit — not only the click."""
    from hyperspace import ui_pad_views
    for view in ("faithful", "cockpit"):
        hits = _drawn(view, _edge_pad())
        at = {h[4]: h[:4] for h in hits}
        for side in ("L", "R"):
            assert at[f"axis:{side}X"] == at[f"axis:{side}Y"] == at[f"pad:{side}STICK"], view
    ctx = ui_pad_views.Ctx(None, None, 0, 0, 100, 100, ui_pad_views.read(None),
                           lambda s: ("", None))
    for src in ("pad:LSTICK", "axis:LX", "axis:LY"):
        ctx.hit(10, 10, 50, 50, src)
    ctx.hit(60, 60, 90, 90, "pad:A")
    tip = ui_pad_views.tip_at(ctx, 20, 20)
    assert all(gamepad.control_name(s) in tip for s in ("pad:LSTICK", "axis:LX", "axis:LY"))
    assert gamepad.control_name("pad:A") not in tip


def _fake_nvg(log: list):
    """A NanoVG that records its transform calls and runs the drawing, as
    `render_nvg_to_frame_buffer` does: (begin, the drawing, end)."""
    from types import SimpleNamespace as NS

    def rec(name):
        return lambda vg, *a: log.append((name, a))

    def render(vg, fb, draw, clear):
        log.append(("begin", ()))
        draw(vg, fb.w, fb.h)
        log.append(("end", ()))
    return NS(save=rec("save"), restore=rec("restore"), translate=rec("translate"),
              scale=rec("scale"),
              nvg_imgui=NS(NvgFramebuffer=lambda vg, w, h, f: NS(w=w, h=h, texture_id=7),
                           render_nvg_to_frame_buffer=render))


def test_the_surface_fits_the_design_space_and_ends_its_frame_on_an_error(monkeypatch):
    """`Surface.render`: the lab's 1000 × 620 fitted to the framebuffer and
    centred (letterboxed); a drawing that raises still restores the
    transform and ends the frame, then the error is raised."""
    from hyperspace import ui_pad_lab, ui_pad_nvg, ui_pad_views
    log: list = []
    surf = ui_pad_nvg.Surface()
    surf.vg, surf.nvg = object(), _fake_nvg(log)
    drew = []
    monkeypatch.setitem(ui_pad_lab.VIEWS, "faithful", lambda pen, r, st: drew.append(pen))
    tex, pen = surf.render("faithful", ui_pad_views.read(None), {}, 2000, 620, "room", 0)
    assert tex == 7 and drew == [pen]
    assert ("scale", (1.0, 1.0)) in log and ("translate", (500.0, 0.0)) in log

    def boom(pen, r, st):
        raise ValueError("a drawing's error")
    monkeypatch.setitem(ui_pad_lab.VIEWS, "faithful", boom)
    log.clear()
    with pytest.raises(ValueError):
        surf.render("faithful", ui_pad_views.read(None), {}, 2000, 620, "room", 1)
    assert [e[0] for e in log] == ["begin", "save", "translate", "scale", "restore", "end"]


def test_the_room_maps_the_drawings_hits_onto_the_screen(rig, monkeypatch):
    """Where NanoVG draws, a hit in the design space lands on the screen
    where the texture shows it: the room's letterboxed rect."""
    from hyperspace import ui_pad_lab, ui_pad_nvg, ui_pad_views
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
    reg = rig.reg
    reg["ui.pad_diagram"].set(True)
    reg["ui.panel"].set(False)
    surf = ui_pad_nvg.surface_of(rig.panel)
    surf.vg, surf.nvg = object(), _fake_nvg([])
    monkeypatch.setitem(ui_pad_lab.VIEWS, "faithful",
                        lambda pen, r, st: (pen.hit(0, 0, 1000, 620, "pad:A"),
                                            pen.hit(500, 310, 10, 10, "pad:B")))
    reg["ui.pad_view"].set(ui_pad_views.VIEWS.index("faithful"))
    c = _pad_frames(rig, monkeypatch)["ctx"]
    s = min(c.w / 1000, c.h / 620)
    ox, oy = c.x + (c.w - 1000 * s) / 2, c.y + (c.h - 620 * s) / 2
    at = {h[4]: h[:4] for h in c.hits}
    assert at["pad:A"] == pytest.approx((ox, oy, ox + 1000 * s, oy + 620 * s))
    assert at["pad:B"] == pytest.approx((ox + 500 * s, oy + 310 * s, ox + 510 * s, oy + 320 * s))
    surf.vg = None                                  # the rig's panel closes without a NanoVG


def test_quiet_rooms_let_go_and_a_failed_start_frees_its_context(rig, monkeypatch):
    """A room not drawn for STALE frames lets its framebuffer go — swept
    each frame even with the pad window off — and a NanoVG made before a
    font failed to load is deleted, not leaked."""
    from imgui_bundle import hello_imgui
    from imgui_bundle import nanovg as nvg

    from hyperspace import ui_pad_nvg
    surf = ui_pad_nvg.Surface()
    surf.fbs = {"old": [object(), (1, 1), 0], "new": [object(), (1, 1), 200]}
    surf.sweep(200)
    assert set(surf.fbs) == {"new"}
    swept = []
    monkeypatch.setattr(ui_pad_nvg, "sweep", lambda panel, frame: swept.append(frame))
    rig.reg["ui.pad_diagram"].set(False)
    frame(rig.panel)
    assert swept

    made, deleted = object(), []
    monkeypatch.setattr(ui_pad_nvg, "_current", lambda: object())
    monkeypatch.setattr(hello_imgui, "init_gl_loader", lambda: None)
    monkeypatch.setattr(nvg.nvg_imgui, "create_nvg_context_hello_imgui", lambda flags: made)
    monkeypatch.setattr(nvg.nvg_imgui, "delete_nvg_context_hello_imgui", deleted.append)
    monkeypatch.setattr(nvg, "create_font", lambda vg, name, path: -1)
    fresh = ui_pad_nvg.Surface()
    assert not fresh.ready() and "would not load" in fresh.failed and fresh.vg is None
    assert deleted == [made]


def test_the_drawings_show_upright_through_real_gl(monkeypatch, gl_window_ok):
    """Real GL (CI runs the suite under Xvfb): what the drawings put at the
    top of the design space is the texture's first row — the row ImGui's
    image shows at its top with the default UVs `_lab` uses — so Faithful
    and Cockpit show upright. (Not the GL rule another renderer's
    framebuffer follows: ui_graph's wireframe flips its UVs; imgui-bundle's
    NanoVG framebuffer is the other way up, and must not be flipped.)"""
    import numpy as np

    from hyperspace import ui_pad_lab, ui_pad_nvg, ui_pad_views
    glfw = pytest.importorskip("glfw")
    moderngl = pytest.importorskip("moderngl")
    if not glfw.init():
        pytest.skip("no display for GL")
    glfw.window_hint(glfw.VISIBLE, False)
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)
    win = glfw.create_window(64, 64, "upright", None, None)
    glfw.default_window_hints()
    if not win:
        pytest.skip("no GL context")
    glfw.make_context_current(win)
    surf = ui_pad_nvg.Surface()
    try:
        assert surf.ready(), surf.failed

        def halves(pen, r, st):                 # the top red, the bottom blue
            pen.rr(0, 0, 1000, 310, 0)
            pen.fill("#ff0000")
            pen.rr(0, 310, 1000, 310, 0)
            pen.fill("#0000ff")
        monkeypatch.setitem(ui_pad_lab.VIEWS, "faithful", halves)
        w, h = 100, 62
        tex, _ = surf.render("faithful", ui_pad_views.read(None), {}, w, h, "upright", 0)
        ctx = moderngl.create_context()
        px = np.frombuffer(ctx.external_texture(tex, (w, h), 4, 0, "f1").read(),
                           np.uint8).reshape(h, w, 4)
        assert px[2, w // 2, 0] > 200 and px[2, w // 2, 2] < 60, px[2, w // 2]        # first row: red
        assert px[-3, w // 2, 2] > 200 and px[-3, w // 2, 0] < 60, px[-3, w // 2]      # last row: blue
    finally:
        surf.close()
        glfw.destroy_window(win)
