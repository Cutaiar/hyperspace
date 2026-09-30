"""learn.py — the armed param and the held question, shared by every
adapter (plan 11 WP5, audit B3 and B4). A hand completes a learn with no
MIDI adapter anywhere; a `band.sel.*` alias learns onto the band it
stands for; the referee's refusal is held for the prompt."""

import json
from types import SimpleNamespace as NS

import pytest

from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.control import Control
from hyperspace.learn import Learn
from hyperspace.library import Library
from hyperspace.params import build_registry
from hyperspace.render import ViewState
from hyperspace.routing import Binding, Bindings


@pytest.fixture()
def rig(tmp_path):
    chain = Analyzer(Analyser())
    control = Control(chain)
    lib = Library(tmp_path)
    reg = build_registry(ViewState(), control, NS(chain=chain), lib.project)
    table = Bindings.load(tmp_path / "bindings.json", legacy_midi=None)
    return NS(reg=reg, control=control, table=table, learn=Learn(reg, table))


def test_learn_source_writes_a_position_route_without_any_midi(rig, tmp_path):
    """A hand completing a learn: a `position` row at depth 1 through the
    table's referee, into the table and no file (plan 13 §3.3: the loaded
    preset's) — no MidiIO exists here (B3). On an owned target it is held
    in `pending`; a new learn forgets it."""
    lrn, t = rig.learn, rig.table
    lrn.arm("view.inst_amp")
    assert lrn.learning == "view.inst_amp"
    lrn.learn_source("hand:3", when="hand:14")
    assert lrn.learning is None and lrn.pending is None
    b = t.owner("view.inst_amp")
    assert (b.source, b.op, b.value, b.when) == ("hand:3", "position", 1.0, "hand:14")
    assert "learned view.inst_amp" in lrn.last and not lrn.refused
    assert not (tmp_path / "bindings.json").exists()
    lrn.arm("view.inst_amp")
    lrn.learn_source("hand:7")
    assert lrn.pending is not None and lrn.pending[1] is b and "replace?" in lrn.last
    assert t.owner("view.inst_amp") is b                       # untouched while it asks
    lrn.arm("no.such.param")
    assert lrn.pending is None                                 # a new learn forgets it
    lrn.learn_source("hand:7")                                 # unknown target: nothing
    assert lrn.learning is None and t.owner("no.such.param") is None
    lrn.learn_source("hand:7")                                 # nothing armed: nothing
    assert lrn.pending is None


def test_a_learned_axis_drives_one_param(rig):
    """Learning an axis onto another param moves it — its other position
    rows go, its push rows stay; learning it again onto the same param is
    no move and no prompt, only the gate refreshed."""
    lrn, t = rig.learn, rig.table
    t.add(Binding("hand:3", "view.bright", "push", 0.5))       # a route on the same axis
    lrn.arm("view.inst_amp")
    lrn.learn_source("hand:3")
    lrn.arm("view.speed")
    lrn.learn_source("hand:3", when="hand:14")                 # moves: inst_amp lets go
    assert t.owner("view.inst_amp") is None and lrn.pending is None
    speed = t.owner("view.speed")
    assert (speed.source, speed.when) == ("hand:3", "hand:14")
    assert t.routes_to("view.bright")[0].op == "push"          # the push row stays
    lrn.arm("view.speed")
    lrn.learn_source("hand:3")                                 # same axis, same param
    assert lrn.pending is None and t.owner("view.speed") is speed and speed.when is None
    assert len(t.routes_to("view.speed")) == 1 and "learned view.speed" in lrn.last


def test_the_prompts_answer_replaces_or_keeps(rig):
    lrn, t = rig.learn, rig.table
    old = t.add(Binding("hand:3", "view.inst_amp", "position"))
    lrn.arm("view.inst_amp")
    lrn.learn_source("hand:7")
    assert lrn.resolve_pending(False) is None                  # Keep
    assert lrn.pending is None and t.owner("view.inst_amp") is old and "kept" in lrn.last
    lrn.arm("view.inst_amp")
    lrn.learn_source("hand:7")
    new = lrn.resolve_pending(True)                            # Replace
    assert new is t.owner("view.inst_amp") and new.source == "hand:7" and old not in t.bindings
    assert lrn.resolve_pending(True) is None                   # nothing pending


def test_a_learn_on_a_band_sel_alias_lands_on_the_selected_band(rig):
    """B4: `band.sel.*` is a non-modulatable alias the router skips, so the
    route goes on the band it stands for — whichever is selected now."""
    lrn, t, reg = rig.learn, rig.table, rig.reg
    assert reg["band.sel.thr"].alias and not reg["band.sel.thr"].modulatable
    rig.control.selb = 2
    lrn.arm("band.sel.thr")
    lrn.learn_source("hand:7")
    assert t.owner("band.sel.thr") is None
    b = t.owner("band.2.thr")
    assert (b.source, b.op) == ("hand:7", "position") and "learned band.2.thr" in lrn.last
    # the referee still sees the real target: a second learn onto the same
    # band through the alias is held against the row that owns it
    rig.control.selb = 2
    lrn.arm("band.sel.thr")
    lrn.learn_source("hand:3")
    assert lrn.pending is not None and lrn.pending[1] is b
    # the rule is the registry's (Registry.real), the one the panel's
    # widgets read through; a registry without one learns the alias as armed
    assert reg.real(reg["band.sel.thr"]) is reg["band.2.thr"]
    reg.real_of = None
    assert Learn(reg, t).target_for("band.sel.thr").id == "band.sel.thr"


# ------------------------------------------ plan 13 WP4: into the loaded preset

def desk_rig(home):
    """The app's construction (tests/test_presets.boot: the startup preset
    loaded) with a MIDI adapter over fake ports on the same table and one
    shared Learn; bindings.json written once so a later write would show."""
    from test_midi import FakeIn, FakeOut
    from test_presets import boot

    from hyperspace.midi import MidiIO

    r = boot(home)
    table = r.router.table
    table.write()
    r.learn = Learn(r.reg, table)
    r.inp, r.out = FakeIn(), FakeOut()
    r.midi = MidiIO(r.reg, table, inp=r.inp, out=r.out, learner=r.learn)
    r.path = table.path
    r.on_disk = (table.path.read_text(), table.path.stat().st_mtime_ns)
    return r


def untouched(r) -> bool:
    return (r.path.read_text(), r.path.stat().st_mtime_ns) == r.on_disk


def test_a_knob_learn_writes_a_desk_row_into_the_loaded_preset(tmp_path):
    """Plan 13 §3.3, D5: a knob learn is a preset-layer row in the live
    table — the control's old preset row and the param's previous knob
    go, the global row on the same knob stays — the loaded preset is dirty
    and bindings.json is untouched; saving the preset writes the row, and
    loading the preset again throws away what was learned since."""
    from test_midi import cc, push

    from hyperspace import preset

    r = desk_rig(tmp_path)
    lib, table, lrn = r.lib, r.router.table, r.learn
    assert lib.current("presets") == "BIG BLUE WAVE" and not lib.is_dirty("presets")
    lrn.arm("view.depth4")
    push(r, cc(0x10, 64))                                   # device knob 1: free on the preset layer
    assert lrn.learning is None and not lrn.refused
    assert "learned view.depth4" in lrn.last and "device knob 1" in lrn.last
    row = next(b for b in table.desk() if b.target == "view.depth4")
    assert (row.source, row.op, row.layer, row.feedback) == ("cc:0:16", "abs", "preset", "ring")
    assert any(b.layer == "global" and b.target == "band.sel.trim" for b in table.midi())
    lrn.arm("view.bright")
    push(r, cc(0x33, 10))                                   # track knob 4, view.pattern_mix's
    assert not any(b.target == "view.pattern_mix" and b.kind == "cc" for b in table.desk())
    assert not any(b.target == "view.bright" and b.number == 0x30 for b in table.desk())
    assert lib.is_dirty("presets") and untouched(r)
    path = lib.overwrite("presets")                         # the head's / the strip's save
    assert path == tmp_path / "presets" / "big-blue-wave.json" and untouched(r)
    saved = json.loads(path.read_text())["desk"]
    assert {"source": "cc:0:16", "target": "view.depth4", "op": "abs",
            "feedback": "ring"} in saved
    assert not lib.is_dirty("presets")
    lrn.arm("view.speed")
    push(r, cc(0x11, 64))                                   # learned after the save…
    assert lib.is_dirty("presets")
    lib.load("presets", "BIG BLUE WAVE")                    # …and thrown away by a load
    assert not any(b.target == "view.speed" and b.number == 0x11 for b in table.desk())
    assert preset.desk_json(table.desk()) == saved and not lib.is_dirty("presets")
    assert untouched(r)


def test_a_knob_learn_replaces_an_any_channel_row_on_the_same_knob(tmp_path):
    """Review of PR #67: a learn replaces every row of its own layer on the
    same physical control (`Binding.overlaps`), an any-channel row
    included. `lfo-breathe`'s desk has ``cc:*:16`` on its Breathe macro;
    learning device knob 1 (``cc:0:16``) leaves one row there, and the knob
    moves the learned param only. The global row on that knob stays."""
    from test_midi import cc, push

    r = desk_rig(tmp_path)
    lib, table, lrn, reg = r.lib, r.router.table, r.learn, r.reg
    lib.load("presets", "lfo-breathe")
    assert [b.target for b in table.desk() if b.source == "cc:*:16"] == ["macro.1"]
    lrn.arm("view.depth4")
    push(r, cc(0x10, 64))
    on_knob = [b for b in table.desk() if b.kind == "cc" and b.number == 0x10]
    assert [(b.source, b.target) for b in on_knob] == [("cc:0:16", "view.depth4")]
    assert any(b.layer == "global" and b.source == "cc:*:16" for b in table.midi())
    macro = reg["macro.1"].norm
    for x in on_knob:
        x.pickup = False
    push(r, cc(0x10, 20), cc(0x10, 110))
    assert reg["view.depth4"].norm == pytest.approx(110 / 127, abs=0.02)
    assert reg["macro.1"].norm == pytest.approx(macro)             # one param, not two
    assert untouched(r)


def test_a_hand_learn_writes_a_route_into_the_loaded_preset(tmp_path):
    """The same for a hand: the route goes into the table through the
    referee — a taken target still asks, Replace / Keep — and neither the
    learn nor the answer writes bindings.json; the preset is dirty until
    saved, and a load throws the learn away."""
    r = desk_rig(tmp_path)
    lib, table, lrn = r.lib, r.router.table, r.learn
    lrn.arm("view.inst_amp")
    lrn.learn_source("hand:3")
    b = table.owner("view.inst_amp")
    assert (b.source, b.op) == ("hand:3", "position") and "into the preset" in lrn.last
    assert lib.is_dirty("presets") and untouched(r)
    lrn.arm("view.inst_amp")
    lrn.learn_source("hand:7")                               # taken: the prompt's question
    assert lrn.pending is not None and table.owner("view.inst_amp") is b
    assert lrn.resolve_pending(False) is None and table.owner("view.inst_amp") is b   # Keep
    lrn.arm("view.inst_amp")
    lrn.learn_source("hand:7")
    new = lrn.resolve_pending(True)                          # Replace
    assert table.owner("view.inst_amp") is new and b not in table.bindings and untouched(r)
    path = r.presets.save_as("HANDS")
    routes = json.loads(path.read_text())["routes"]
    assert {"source": "hand:7", "target": "view.inst_amp", "op": "position"} in routes
    assert not lib.is_dirty("presets") and untouched(r)
    lrn.arm("view.speed")
    lrn.learn_source("hand:9")
    lib.load("presets", "HANDS")
    assert table.owner("view.speed") is None and table.owner("view.inst_amp").source == "hand:7"
    assert untouched(r)


def test_learn_refuses_the_global_layer_and_invariant_controls(tmp_path):
    """D5, D6: with the global layer up, and on an invariant control — a
    fader, SHIFT's own note — a learn is refused: nothing changes (the
    table, the layer, the param, the file, the preset's dot) and the
    reason is in `learner.last`."""
    from test_midi import cc, note, push, shift

    from hyperspace import apc40

    r = desk_rig(tmp_path)
    lib, table, lrn, reg = r.lib, r.router.table, r.learn, r.reg

    def rows():
        return [(b.to_json(), b.layer) for b in table.bindings]
    shift(r)
    assert table.layer == "global"
    before, depth4 = rows(), reg["view.depth4"].value
    lrn.arm("view.depth4")
    push(r, cc(0x30, 90))                                    # track knob 1, SHIFT on
    assert lrn.learning is None and lrn.refused
    assert lrn.last == ("K1 (track knob 1) is on the global layer (the session's) — "
                        "latch SHIFT off to learn into the preset")
    assert rows() == before and table.layer == "global" and reg["view.depth4"].value == depth4
    shift(r)
    assert table.layer == "preset"
    lrn.arm("view.depth4")
    push(r, cc(apc40.CC_FADER, 64, channel=2))               # track fader 3
    assert lrn.refused and lrn.last == "S3 (track fader 3) is invariant (the session's) — not learned"
    lrn.arm("view.depth4")
    push(r, note(apc40.N_SHIFT))                             # SHIFT itself
    assert lrn.refused and lrn.last == "⇧ (SHIFT) is invariant (the session's) — not learned"
    assert table.layer == "preset"                           # the press did not latch
    push(r, note(apc40.N_SHIFT, 0))
    assert rows() == before and reg["view.depth4"].value == depth4
    assert not lib.is_dirty("presets") and untouched(r)
    lrn.arm("view.depth4")                                   # and a good learn clears the flag
    push(r, cc(0x10, 64))
    assert not lrn.refused and "learned view.depth4" in lrn.last
