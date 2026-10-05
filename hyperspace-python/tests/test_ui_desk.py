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

from hyperspace import apc40, routing, ui_desk
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
    it adds no widget ids of its own (hit-tested, not buttons)."""
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
    assert ids == []
    panel.reg["ui.desk"].set(False)
    frame(panel)
    assert len(calls) == 4


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
