# ruff: noqa: F811 — `rig` is test_ui_shell's fixture, taken as each test's argument
"""The APC40 drawn on screen (plan 14 WP7, decision 25 (a)).

The layout (`apc40.LAYOUT`): one entry per control the protocol names,
none overlapping, a unique short glyph each, and a glyph for every MIDI
row shipped. The diagram (ui_desk.py): what it lights is the layer that
is up — a factory preset's desk plus the invariant controls, then the
global layer after SHIFT — read from the table with no MIDI device. The
ROUTING rows print the glyph. Headless imgui, a library on tmp_path.
"""

import json

from imgui_bundle import imgui
from test_ui_shell import (
    frame,
    rig,  # noqa: F401 — the headless panel fixture
)

from hyperspace import apc40, routing, ui, ui_desk
from hyperspace.app import CONTROL_SIZE
from hyperspace.library import FACTORY
from hyperspace.routing import Binding

# ---------------------------------------------------------------- the layout


def _protocol_sources() -> set[str]:
    """Every control the protocol table in apc40.py names, as a source."""
    per_track = [*apc40.N_CLIP, apc40.N_CLIPSTOP, apc40.N_SELECT, apc40.N_ACTIVATOR,
                 apc40.N_SOLO, apc40.N_ARM]
    one = [*apc40.N_SCENE, apc40.N_STOP_ALL, apc40.N_MASTER_SEL, apc40.N_SHIFT,
           *apc40.OTHER_BUTTONS]
    out = {f"note:{ch}:{n}" for ch in range(8) for n in per_track}
    out |= {f"note:0:{n}" for n in one}
    out |= {f"cc:{ch}:{apc40.CC_FADER}" for ch in range(8)}
    out |= {f"cc:0:{n}" for n in (apc40.CC_MASTER, apc40.CC_XFADE, apc40.CC_CUE)}
    out |= {f"cc:0:{n}" for n in apc40.TRACK_KNOBS} | {f"cc:*:{n}" for n in apc40.DEVICE_KNOBS}
    return out


def test_one_layout_entry_per_protocol_control():
    """137 controls: 80 per-track buttons, the scene column, 22 other
    buttons and SHIFT, nine faders, the crossfader, the cue knob, 16 knobs;
    every note constant of the protocol table is on the layout."""
    srcs = [c.source for c in apc40.LAYOUT]
    assert len(srcs) == len(set(srcs)) == 137
    assert set(srcs) == _protocol_sources()
    notes = {v for k, v in vars(apc40).items() if k.startswith("N_") and isinstance(v, int)}
    notes |= {n for k, v in vars(apc40).items() if k.startswith("N_") and isinstance(v, list)
              for n in v}
    assert notes <= {int(s.rsplit(":", 1)[1]) for s in srcs if s.startswith("note:")}
    for c in apc40.LAYOUT:
        assert c.kind in ("knob", "fader", "button", "grid"), c
        assert apc40.control_name(c.source) == c.name, c        # Akai's name for every one


def test_no_two_layout_entries_overlap():
    cs = apc40.LAYOUT
    for i, a in enumerate(cs):
        assert a.w > 0 and a.h > 0 and a.x >= 0 and a.y >= 0, a
        for b in cs[i + 1:]:
            apart = (a.x + a.w <= b.x or b.x + b.w <= a.x
                     or a.y + a.h <= b.y or b.y + b.h <= a.y)
            assert apart, f"{a} overlaps {b}"


def test_glyphs_are_unique_and_short():
    gs = [c.glyph for c in apc40.LAYOUT]
    assert len(set(gs)) == len(gs)
    assert max(map(len, gs)) <= 5
    # the scheme of decision 25 (a)
    assert {f"K{k}" for k in range(1, 9)} | {f"D{k}" for k in range(1, 9)} <= set(gs)
    assert {f"S{k}" for k in range(1, 9)} | {"SM", "X", "C", "⇧"} <= set(gs)
    assert {f"B{k}" for k in range(1, 23)} <= set(gs)
    assert {f"G{r}·{c}" for r in range(1, 11) for c in range(1, 9)} <= set(gs)
    assert {f"G{r}·9" for r in range(1, 8)} <= set(gs)


def test_the_glyph_resolves_a_row_on_any_channel():
    g = apc40.glyph
    assert g("cc:*:16") == g("cc:0:16") == g("cc:5:16") == "D1"        # a device knob
    assert g("cc:0:48") == g("cc:*:48") == "K1"                          # a track knob
    assert g("cc:3:7") == "S4" and g("note:2:50") == "G8·3" and g("note:0:82") == "G1·9"
    assert g("note:0:98") == "⇧" and g("note:0:99") == "B20" and g("cc:0:15") == "X"
    assert g("note:*:53") == "G1·*" and g("cc:*:7") == "S*"               # a whole strip row
    assert g("cc:0:99") is None and g("key:A") is None and g("note:0:1") is None
    assert apc40.named("cc:*:18") == "D3 (device knob 3)"


def _shipped_midi_rows() -> list[str]:
    srcs = [r["source"] for r in apc40.DEFAULT_MAP]
    srcs += [b.source for b in routing.factory_desk("apc40")]
    session = json.loads(routing.FACTORY_FILE.read_text())
    srcs += [r["source"] for r in session["bindings"]]
    for f in sorted((FACTORY / "presets").glob("*.json")):
        srcs += [r["source"] for r in json.loads(f.read_text()).get("desk") or []]
    return [s for s in srcs if s.startswith(("cc:", "note:"))]


def test_every_midi_row_shipped_has_a_glyph():
    """DEFAULT_MAP, the factory session table and every factory preset's desk."""
    srcs = _shipped_midi_rows()
    assert len(srcs) > 200
    assert [s for s in srcs if apc40.glyph(s) is None] == []


# ---------------------------------------------------------------- the diagram

def _glyphs(rows) -> set[str]:
    return {c.glyph for b in rows for c in apc40.controls(b.source)}


def test_the_diagram_lights_the_loaded_presets_desk_and_the_invariant_controls(rig):
    lib, table, panel = rig.lib, rig.router.table, rig.panel
    lib.load("presets", "TRIP")
    assert table.layer == "preset" and table.desk()
    inv = _glyphs(table.invariant_rows())
    assert "⇧" in inv and "S1" in inv
    frame(panel, "routing")
    lit = ui_desk.lit_cached(panel, table)
    assert set(lit) == _glyphs(b for b in table.desk() if b.enabled) | inv
    assert "D1" in lit and lit["D1"].layer == "preset"        # TRIP's device knobs
    # SHIFT: the global layer's rows instead of the preset's
    table.toggle_layer()
    frame(panel)
    lit = ui_desk.lit_cached(panel, table)
    glob = [b for b in table.midi() if b.layer == "global" and b.enabled]
    assert set(lit) == (_glyphs(glob) - inv) | inv
    assert lit["D1"].target == "band.sel.trim"                # the band strip under SHIFT
    assert "K6" not in lit                                    # free on the global layer: dark
    table.toggle_layer()
    assert set(ui_desk.lit_cached(panel, table)) >= {"D1"}


def test_the_diagram_follows_an_edit_and_needs_no_midi_device(rig):
    """The panel has no MIDI adapter; a learn-like bind and a removal show
    at once (the cache keys on the table's serials and rows)."""
    panel, table = rig.panel, rig.router.table
    assert panel.midi is None
    frame(panel)
    assert "K6" in ui_desk.lit_cached(panel, table)           # the fresh preset's view faders
    k6 = next(b for b in table.desk() if b.source == "cc:0:53")
    table.remove(k6)
    assert "K6" not in ui_desk.lit_cached(panel, table)
    table.bind(Binding("cc:0:53", "view.speed", "abs", feedback="ring", layer="preset"),
               write=False)
    assert ui_desk.lit_cached(panel, table)["K6"].target == "view.speed"


def test_the_hover_names_glyph_param_layer_and_akais_name(rig):
    table = rig.router.table
    c = next(c for c in apc40.LAYOUT if c.glyph == "K1")
    b = ui_desk.lit(table)["K1"]
    assert ui_desk.label(table, c, b) == f"K1 · {b.target} · preset layer\ntrack knob 1"
    dark = next(c for c in apc40.LAYOUT if c.glyph == "B7")        # device ◀: no row
    assert "B7" not in ui_desk.lit(table)
    assert "unmapped — dark" in ui_desk.label(table, dark, None)
    # the clip-stop row is the SAVE AS bar (plan 15 WP4): eight invariant rows
    for k in range(1, 9):
        c = next(c for c in apc40.LAYOUT if c.glyph == f"G6·{k}")
        b = ui_desk.lit(table)[c.glyph]
        assert ui_desk.label(table, c, b) == f"G6·{k} · preset.save_new · invariant\nclip stop {k}"
    s = next(c for c in apc40.LAYOUT if c.glyph == "⇧")
    assert ui_desk.label(table, s, ui_desk.lit(table)["⇧"]).startswith("⇧ · desk.shift · invariant")


def test_the_diagram_draws_on_both_layers_and_hides(rig, monkeypatch):
    """It draws with the cheat sheet on and off, and `ui.desk` hides it;
    the only widget id it adds is its header chip (the controls are
    hit-tested, not buttons)."""
    panel = rig.panel
    calls = []
    real = ui_desk.diagram
    monkeypatch.setattr(ui_desk, "diagram", lambda p: (calls.append(1), real(p))[1])
    ids: list[int] = []
    for fn in ("button", "invisible_button", "checkbox", "selectable"):
        orig = getattr(imgui, fn)

        def rec(label, *a, _real=orig, **k):
            ids.append(label)
            return _real(label, *a, **k)
        monkeypatch.setattr(imgui, fn, rec)
    for sheet in (True, False):
        panel.reg["ui.cheatsheet"].set(sheet)
        for layer in ("preset", "global"):
            rig.router.table.set_layer(layer)
            frame(panel)
    assert len(calls) == 4
    ids.clear()
    imgui.new_frame()
    real(panel)
    imgui.end_frame()
    assert ids == ["big##desk"]
    panel.reg["ui.desk"].set(False)
    frame(panel)
    assert len(calls) == 4


def test_the_desk_does_not_jump_when_the_sheet_comes_up(rig, monkeypatch):
    """Plan 16 WP7: the sheet is off at launch, and the frame `/` first
    brings it up the desk is already where it stays — above the sheet's
    real height, not the height imgui gives a window it has not laid out."""
    panel = rig.panel
    rects = []
    real = ui_desk._body

    def body(p, table):
        pos, size = imgui.get_window_pos(), imgui.get_window_size()
        rects.append((pos.x, pos.y, size.x, size.y))
        return real(p, table)
    monkeypatch.setattr(ui_desk, "_body", body)
    assert panel.cheatsheet is False
    for _ in range(2):
        frame(panel)
    off = rects[-1]
    panel.reg["ui.cheatsheet"].set(True)
    for _ in range(3):
        frame(panel)
    first, second, third = rects[-3:]
    assert first == second == third
    assert first[1] < off[1] - 100                     # it moved up by a whole sheet, at once
    # …and the height it stands on is the sheet window's own, once laid out
    imgui.new_frame()
    imgui.begin("##cheatsheet")
    laid_out = imgui.get_window_height()
    imgui.end()
    imgui.end_frame()
    assert abs(panel._sheet_h - laid_out) <= 1.0
    panel.reg["ui.cheatsheet"].set(False)
    frame(panel)
    assert rects[-1] == off


def test_the_routing_rows_print_the_glyph(rig, monkeypatch):
    """A desk row and a session row: the glyph first, the param after it."""
    texts: list[str] = []
    real_text, real_col = imgui.text, imgui.text_colored
    monkeypatch.setattr(imgui, "text", lambda s: (texts.append(s), real_text(s))[1])
    monkeypatch.setattr(imgui, "text_colored",
                        lambda c, s: (texts.append(s), real_col(c, s))[1])
    rig.lib.load("presets", "TRIP")
    frame(rig.panel, "routing")
    frame(rig.panel)
    desk = rig.router.table.desk()
    assert {apc40.glyph(b.source) for b in desk} <= set(texts)
    assert "S1" in texts and "⇧" in texts                     # the session's rows
    assert "device knob 1" not in texts                       # Akai's names: tooltips only


# ------------------------------------------- plan 17 WP4: the desk, big

def test_the_desk_takes_the_room_it_has():
    """`room` (fork 1): left of the panel and never under `MIN_W`; the
    whole window with the panel hidden; above the cheat sheet with the
    panel open, beside it with the panel hidden; a layout unit never
    taller than it is wide."""
    room, E = ui_desk.room, ui_desk.EDGE
    display = tuple(float(v) for v in CONTROL_SIZE)             # 960 × 900
    panel_x = display[0] - ui.PANEL_W - 12

    def unit(w, h):
        return ((w - 2 * ui_desk.PAD) / apc40.LAYOUT_W,
                (h - 2 * ui_desk.PAD - ui_desk.HEAD_H) / apc40.LAYOUT_H)
    # the panel open: it ends 12 px left of the panel, bottom-left, glyphs only
    x, y, w, h = room(display, panel_x, None)
    assert x == E and x + w == panel_x - E and w >= ui_desk.MIN_W
    assert y + h == display[1] - E and y >= E
    ux, uy = unit(w, h)
    assert uy <= ux + 1e-6 and ux < ui_desk.LABEL_UNIT
    # hidden: the whole window, units wide enough for labels
    x, y, w, h = room(display, None, None)
    assert (x, w) == (E, display[0] - 2 * E) and y == E and y + h == display[1] - E
    ux, uy = unit(w, h)
    assert uy <= ux + 1e-6 and ux >= ui_desk.LABEL_UNIT
    # a wide control window with the panel open: labelled beside the panel
    wide = (1512.0, 900.0)
    x, y, w, h = room(wide, wide[0] - ui.PANEL_W - 12, None)
    assert unit(w, h)[0] >= ui_desk.LABEL_UNIT and x + w == wide[0] - ui.PANEL_W - 12 - E
    # the sheet on, the panel open: above it
    sheet = (372.0, 620.0)
    x, y, w, h = room(display, panel_x, sheet)
    assert x == E and y + h == display[1] - E - sheet[1] - ui_desk.GAP
    assert h >= ui_desk.MIN_H
    # the sheet on, the panel hidden: beside it, full height
    x, y, w, h = room(display, None, sheet)
    assert x == E + sheet[0] + ui_desk.GAP and x + w == display[0] - E
    assert y + h == display[1] - E
    ux, uy = unit(w, h)
    assert uy <= ux + 1e-6
    # a panel dragged far left: never narrower than MIN_W
    assert room(display, 100.0, None)[2] == ui_desk.MIN_W
    # a short, wide window: the height is what there is, the unit flatter than wide
    x, y, w, h = room((1600.0, 400.0), None, None)
    assert h == 400.0 - 2 * E and unit(w, h)[1] < unit(w, h)[0]


class _Ink:
    """The window's draw list, recording the text drawn through it."""

    def __init__(self, dl, texts):
        self._dl, self._texts = dl, texts

    def add_text(self, pos, col, text):
        self._texts.append(text)
        return self._dl.add_text(pos, col, text)

    def __getattr__(self, name):
        return getattr(self._dl, name)


def _desk_frames(rig, monkeypatch, n=3) -> dict:
    """Draw `n` frames and return what the desk window was and drew on the
    last: its rect, its scroll range, the text on its draw list."""
    out: dict = {"texts": []}
    real_body, real_dl = ui_desk._body, imgui.get_window_draw_list

    def body(p, table):
        out["texts"].clear()
        pos, size = imgui.get_window_pos(), imgui.get_window_size()
        with monkeypatch.context() as m:
            m.setattr(imgui, "get_window_draw_list", lambda: _Ink(real_dl(), out["texts"]))
            real_body(p, table)
        out["rect"] = (pos.x, pos.y, size.x, size.y)
        out["scroll"] = (imgui.get_scroll_max_x(), imgui.get_scroll_max_y())
    monkeypatch.setattr(ui_desk, "_body", body)
    for _ in range(n):
        frame(rig.panel)
    monkeypatch.setattr(ui_desk, "_body", real_body)
    return out


def test_the_big_desk_labels_every_lit_control_and_never_scrolls(rig, monkeypatch):
    """Panel hidden at the control size, TRIP loaded: the desk is the
    whole window; a label is drawn for each lit control (one for a run of
    pads that say the same) and none for a dark one; the window has no
    scroll range. On both layers."""
    panel, table, reg = rig.panel, rig.router.table, rig.reg
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
    rig.lib.load("presets", "TRIP")
    reg["ui.panel"].set(False)
    glyphs = {c.glyph for c in apc40.LAYOUT}
    for layer in ("preset", "global"):
        table.set_layer(layer)
        got = _desk_frames(rig, monkeypatch)
        assert got["rect"] == (12.0, 12.0, CONTROL_SIZE[0] - 24.0, CONTROL_SIZE[1] - 24.0)
        assert got["scroll"] == (0.0, 0.0), layer
        st = ui_desk._state(panel)
        assert st["unit"][0] >= ui_desk.LABEL_UNIT and st["unit"][1] <= st["unit"][0]
        lit = ui_desk.lit_cached(panel, table)
        says = {g: ui_desk.text(reg, b) for g, b in lit.items()}
        assert len(lit) > 80 and all(says.values())
        # a label for every lit control: the eight clip-stop pads share one
        assert set(st["labels"]) == set(says.values()), layer
        stop = [says[f"G6·{k}"] for k in range(1, 9)]
        assert len(set(stop)) == 1 and st["labels"].count(stop[0]) == 1
        assert len(st["labels"]) == len(lit) - 7, layer
        # what reached the draw list: every glyph (dark ones too), and
        # the labels' lines — nothing else, so a dark control has no label
        drawn = got["texts"]
        assert glyphs <= set(drawn)
        words = [t for t in drawn if t not in glyphs]
        assert len(words) >= len(st["labels"])
        for t in words:
            head = t.rstrip("…").split(" ")[0].rstrip("…")
            assert any(head in v for v in says.values()), (layer, t)
        dark = [c.glyph for c in apc40.LAYOUT if c.glyph not in lit]
        assert dark and drawn.count(dark[0]) == 1
    # the layer changes what is named: TRIP's knobs, then the session's
    table.set_layer("preset")
    _desk_frames(rig, monkeypatch, 1)
    assert "FX mix" in ui_desk._state(panel)["labels"]
    assert "TRIP" in ui_desk._state(panel)["labels"]             # the bank row: the presets' names
    table.set_layer("global")
    _desk_frames(rig, monkeypatch, 1)
    labels = ui_desk._state(panel)["labels"]
    assert "FX mix" not in labels and "Steadiness" in labels and "BPM" in labels


def test_the_small_desk_draws_glyphs_only(rig, monkeypatch):
    """Panel open at the control size: today's drawing — no label — in the
    room left of the panel, never over it."""
    panel = rig.panel
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
    rig.lib.load("presets", "TRIP")
    got = _desk_frames(rig, monkeypatch)
    st = ui_desk._state(panel)
    assert st["labels"] == [] and st["unit"][0] < ui_desk.LABEL_UNIT
    glyphs = {c.glyph for c in apc40.LAYOUT}
    assert set(got["texts"]) == glyphs
    x, y, w, h = got["rect"]
    assert panel._panel_x == CONTROL_SIZE[0] - ui.PANEL_W - 12
    assert x == 12.0 and x + w <= panel._panel_x - 12.0 + 1e-6 and w >= ui_desk.MIN_W
    assert y + h == CONTROL_SIZE[1] - 12.0 and got["scroll"] == (0.0, 0.0)
    assert st["unit"][1] <= st["unit"][0] + 1e-6
    # the chip hides the panel; the next frames the desk is big and its chip brings it back
    assert panel.open
    panel.reg["ui.panel"].set(False)
    got = _desk_frames(rig, monkeypatch)
    assert got["rect"][2] == CONTROL_SIZE[0] - 24.0 and ui_desk._state(panel)["labels"]


def test_a_controls_text(rig):
    """`text` (fork 8): an enum `set` row reads the value's name, a `step`
    row the label and the step, anything else the param's label, a
    missing param its id. `wrap`: at most the lines given, broken at
    spaces, each cut to the width; a step keeps its amount."""
    reg = rig.reg
    text = ui_desk.text
    names = reg["view.shape"].names
    assert text(reg, Binding("note:3:56", "view.shape", "set", 3.0)) == names[3]
    bank = reg["preset.select"].names
    assert text(reg, Binding("note:4:53", "preset.select", "set", 4.0)) == bank[4]
    assert text(reg, Binding("note:0:94", "view.bright", "step", 3.0)) == "Brightness +3"
    assert text(reg, Binding("note:0:95", "view.bright", "step", -3.0)) == "Brightness -3"
    assert text(reg, Binding("cc:0:48", "view.bright", "abs")) == "Brightness"
    assert text(reg, Binding("cc:*:18", "fx.kaleido.segments", "abs")) \
        == reg["fx.kaleido.segments"].label
    assert text(reg, Binding("cc:0:49", "no.such.param", "abs")) == "no.such.param"
    assert text(reg, Binding("note:0:91", "view.shape", "set", 99.0)) == reg["view.shape"].label
    # the hover carries the words too
    c = next(c for c in apc40.LAYOUT if c.glyph == "D3")
    b = Binding("cc:*:18", "fx.kaleido.segments", "abs", layer="preset")
    assert ui_desk.label(rig.router.table, c, b, reg) == (
        f"D3 · fx.kaleido.segments · {reg['fx.kaleido.segments'].label} · preset layer\n"
        "device knob 3")
    # wrap, measured in the current font
    imgui.new_frame()
    wrap, w = ui_desk.wrap, lambda t: imgui.calc_text_size(t).x
    wide = w("Kaleidoscope") + 2
    assert wrap("Kaleidoscope segments", wide, 2) == ["Kaleidoscope", "segments"]
    assert wrap("Zoom burst amount", w("Zoom burst") + 2, 2) == ["Zoom burst", "amount"]
    assert wrap("Hue", wide, 2) == ["Hue"] and wrap("", wide, 2) == []
    one = wrap("Kaleidoscope segments", wide, 1)
    assert len(one) == 1 and one[0].endswith("…") and w(one[0]) <= wide
    three = wrap("Save as a new preset", w("Save as") + 2, 2)
    assert three[0] == "Save as" and three[1].endswith("…") and w(three[1]) <= w("Save as") + 2
    narrow = wrap("Kaleidoscope segments", w("Kaleid"), 2)
    assert len(narrow) == 2 and all(w(r) <= w("Kaleid") for r in narrow)
    assert narrow[0].endswith("…")
    cut = wrap("Brightness +3", w("Bright +3"), 1)                # a step keeps its amount
    assert cut[0].endswith("… +3") and w(cut[0]) <= w("Bright +3")
    assert ui_desk.is_cut("Brightness +3", cut) and not ui_desk.is_cut("Hue  cycle", ["Hue", "cycle"])
    assert ui_desk.label_px(67) == 0.2 * 67 and ui_desk.label_px(20) == 11 \
        and ui_desk.label_px(200) == 18
    imgui.end_frame()
