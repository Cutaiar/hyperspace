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
from hyperspace.learn import PUSH_DEPTH, Learn, centred_target
from hyperspace.library import Library
from hyperspace.params import Kind, build_registry
from hyperspace.render import ViewState
from hyperspace.routing import Binding, Bindings, Router


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
    """Learning an axis onto another param moves it — its other performer
    rows go, push or position (plan 18 fork 7), and the status line names
    the params they were on; another axis's rows stay. A row of this axis
    that is switched off goes too (as a switched-off position row always
    did), so a learn never leaves the route in the table twice. Learning
    it again onto the same param is no move and no prompt, only the gate
    refreshed."""
    lrn, t = rig.learn, rig.table
    t.add(Binding("hand:3", "view.bright", "push", 0.5))       # a hand-written push, same axis
    other = t.add(Binding("hand:7", "view.depth4", "push", 0.5))   # another axis
    lfo = t.add(Binding("lfo:3", "fx.mix", "push", 0.2))       # the same number, another scheme
    off = t.add(Binding("hand:3", "camera.zoom", "push", 0.3, enabled=False))
    lrn.arm("view.inst_amp")
    lrn.learn_source("hand:3")                                 # a position row (today's)
    assert lrn.last == ("learned view.inst_amp ← hand 3 positions "
                        "(into the preset; moved from view.bright, camera.zoom)")
    assert not t.routes_to("view.bright")                      # the push row went with it
    assert off not in t.bindings                               # and the one switched off
    twin = t.add(Binding("hand:3", "view.speed", "position", enabled=False))
    lrn.arm("view.speed")
    lrn.learn_source("hand:3", when="hand:14", centred=True)   # moves: inst_amp lets go
    assert t.owner("view.inst_amp") is None and lrn.pending is None
    speed = t.owner("view.speed")
    assert (speed.source, speed.op, speed.value, speed.when) == ("hand:3", "push", 0.25, "hand:14")
    assert lrn.last == ("learned view.speed ← hand 3 pushes +0.25 while hand:14 "
                        "(into the preset; moved from view.inst_amp)")
    assert twin not in t.bindings and t.routes_to("view.speed") == [speed]   # not held twice
    lrn.arm("camera.yaw")
    lrn.learn_source("hand:3", centred=True)                   # a push row moves too
    assert t.owner("view.speed") is None and t.owner("camera.yaw").source == "hand:3"
    assert lrn.last.endswith("(into the preset; moved from view.speed)")
    assert [b for b in t.of("hand", "lfo") if b.source != "hand:3"] == [other, lfo]
    yaw = t.owner("camera.yaw")
    lrn.arm("camera.yaw")
    lrn.learn_source("hand:3", when="hand:14")                 # same axis, same param
    assert lrn.pending is None and t.owner("camera.yaw") is yaw and yaw.when == "hand:14"
    assert len(t.routes_to("camera.yaw")) == 1
    assert lrn.last == "learned camera.yaw ← hand 3 pushes +0.25 while hand:14 (into the preset)"


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


# ------------------------------------------- plan 18 WP3: a learn's default

def played(rig, u: float, rest: float, lane: int = 3) -> None:
    """One frame of the modulation pass with the hand lane `lane` reading
    `u` and resting at `rest`, as the hands adapter publishes them."""
    router = Router(rig.reg, rig.table)
    vec, rests = [float("nan")] * 8, [0.0] * 8
    vec[lane], rests[lane] = u, rest
    router.feed("hand", vec)
    router.rests["hand"] = rests
    router.modulate()
    rig.reg.apply()


def learned(rig, pid: str, source: str = "hand:3", **kw) -> Binding:
    rig.learn.arm(pid)
    rig.learn.learn_source(source, **kw)
    assert rig.learn.pending is None and not rig.learn.refused
    return rig.table.owner(pid)


def test_a_centred_axis_learns_as_a_push_about_the_base_at_the_learn_depth(rig):
    """The rule's first column: a centred axis (roll) on a continuous param
    lands a push at the depth the adapter names, with no rest of its own,
    so it is centred where the axis rests. A level hand leaves the base;
    the ends move it ±depth/2 of the throw. And the session's complaint in
    its own numbers: on `rot.rate.XY` from 1× a level hand reads 1× (the
    position row read 0×: the plane stopped) and the ends are −15.64× and
    +17.64× (they were ±66.56×)."""
    reg = rig.reg
    b = learned(rig, "view.speed", centred=True, depth=0.25)
    assert (b.op, b.value, b.rest, b.when, b.scale) == ("push", 0.25, None, None, None)
    assert b == Binding("hand:3", "view.speed", "push", 0.25)
    p = reg["view.speed"]
    base = p.norm
    played(rig, 0.5, 0.5)
    assert p.eff_norm == pytest.approx(base) and p.norm == pytest.approx(base)
    played(rig, 1.0, 0.5)
    assert p.eff_norm == pytest.approx(base + 0.125) and p.norm == pytest.approx(base)
    played(rig, 0.0, 0.5)
    assert p.eff_norm == pytest.approx(base - 0.125)
    # the rest is the axis's, read every frame: move it and the push follows
    played(rig, 0.3, 0.3)
    assert p.eff_norm == pytest.approx(base)
    # rotation, from the preset's 1×
    rig.table.remove(b)
    rate = reg["rot.rate.XY"]
    rate.set(1.0)
    b = learned(rig, "rot.rate.XY", centred=True, depth=0.25)
    assert (b.op, b.value, b.rest) == ("push", 0.25, None)
    for u, want in ((0.5, 1.0), (1.0, 17.64), (0.0, -15.64), (0.6, 4.328)):
        played(rig, u, 0.5)
        assert rate.value == pytest.approx(want, abs=1e-3), u
        assert rate.base == pytest.approx(1.0)
    # the row before this package, on the same readings
    rig.table.remove(b)
    rig.table.add(Binding("hand:3", "rot.rate.XY", "position", 1.0))
    for u, want in ((0.5, 0.0), (1.0, 66.56), (0.0, -66.56)):
        played(rig, u, 0.5)
        assert rate.value == pytest.approx(want, abs=1e-3), u


def test_a_one_sided_axis_on_a_one_sided_param_is_still_the_fader(rig):
    """Height on brightness: today's row, field for field — whatever depth
    the adapter named, and when it named nothing at all."""
    today = Binding("hand:7", "view.bright", "position", 1.0, when="hand:14")
    b = learned(rig, "view.bright", "hand:7", when="hand:14", centred=False, depth=0.25)
    assert b == today and b.rest is None
    rig.table.remove(b)
    assert learned(rig, "view.bright", "hand:7", when="hand:14") == today
    p = rig.reg["view.bright"]
    played(rig, 1.0, 0.0, lane=7)                # no gate lane fed: shut, the base shows
    assert not p.modulated
    rig.table.owner("view.bright").when = None
    for u in (0.0, 0.4, 1.0):                    # the hand is the fader, end to end
        played(rig, u, 0.0, lane=7)
        assert p.eff_norm == pytest.approx(u)
    for pid in ("view.speed", "view.inst_amp", "camera.zoom", "fx.mix"):
        b = learned(rig, pid, "hand:2")          # neither keyword: today's row
        assert b == Binding("hand:2", pid, "position", 1.0), pid


def test_a_one_sided_axis_on_a_zero_centred_range_pushes_up_from_the_base(rig):
    """Height on a rate, an angle or a pan: a push from the axis's rest (the
    bottom), so a low hand adds nothing and a high one adds up to the
    depth — where the position row started at the bottom of the range
    (−66.56× on `rot.rate.XY`). With no keyword at all it is the same row
    at `PUSH_DEPTH`."""
    reg = rig.reg
    for pid in ("rot.rate.XY", "camera.yaw", "camera.pan.x"):
        b = learned(rig, pid, "hand:7", centred=False, depth=0.25)
        assert (b.op, b.value, b.rest) == ("push", 0.25, None), pid
        p = reg[pid]
        base = p.norm
        played(rig, 0.0, 0.0, lane=7)
        assert p.eff_norm == pytest.approx(base), pid       # a reading of 0 adds nothing
        played(rig, 1.0, 0.0, lane=7)
        assert p.eff_norm == pytest.approx(base + 0.25), pid
        rig.table.remove(b)
    rate = reg["rot.rate.XY"]
    rate.set(1.0)
    b = learned(rig, "rot.rate.XY", "hand:7")
    assert b == Binding("hand:7", "rot.rate.XY", "push", PUSH_DEPTH)
    for u, want in ((0.0, 1.0), (0.1, 4.328), (1.0, 34.28)):
        played(rig, u, 0.0, lane=7)
        assert rate.value == pytest.approx(want, abs=1e-3), u


def test_a_discrete_target_keeps_the_position_row(rig):
    """A toggle, an enum and a trigger keep the fader from any axis: a
    push of 0.25 about a toggle's base never crosses `MOD_ON`, so that
    learn would land and do nothing."""
    from hyperspace.params import MOD_ON

    kinds = {"view.plane.XY": Kind.TOGGLE, "view.shape": Kind.ENUM, "camera.reset": Kind.TRIGGER}
    for pid, kind in kinds.items():
        assert rig.reg[pid].kind is kind
        for centred in (True, False):
            b = learned(rig, pid, centred=centred, depth=0.25)
            assert b == Binding("hand:3", pid, "position", 1.0), (pid, centred)
            rig.table.remove(b)
    assert PUSH_DEPTH * 0.5 < MOD_ON             # why: half a throw of the push from "off"


def test_a_whole_number_param_keeps_the_position_row(rig):
    """Review of PR #100: a whole-number param is stepped too. A push of
    0.25 about `dream.steps` (1–3) is a quarter of a step each way and
    never reaches the next one — the learn would land and do nothing — so
    it keeps the fader, which reaches every step."""
    p = rig.reg["dream.steps"]
    assert p.integer and (p.lo, p.hi) == (1, 3)
    p.set(2)
    rig.table.add(Binding("hand:3", "dream.steps", "push", 0.25))
    seen = set()
    for u in (0.0, 0.25, 0.5, 0.75, 1.0):
        played(rig, u, 0.5)
        seen.add(int(p.value))
    assert seen == {2}                           # the push that is not learned: stuck
    rig.table.remove(rig.table.owner("dream.steps"))
    for pid in ("view.instances", "dream.steps"):            # the axis ends on dream.steps
        b = learned(rig, pid, centred=True, depth=0.25)
        assert b == Binding("hand:3", pid, "position", 1.0), pid
    seen = set()
    for u in (0.0, 0.5, 1.0):
        played(rig, u, 0.5)
        seen.add(int(p.value))
    assert seen == {1, 2, 3}


def test_centred_target_reads_the_declared_range(rig):
    """By declaration only — no taper, not log, lo == −hi; never the id."""
    reg = rig.reg
    yes = [f"rot.rate.{pl}" for pl in ("XY", "XZ", "YZ", "XW", "YW", "ZW")]
    yes += ["camera.yaw", "camera.pitch", "camera.pan.x", "camera.pan.y", "dream.hue"]
    for pid in yes:
        assert centred_target(reg[pid]), pid
    for pid in ("view.speed", "view.bright", "camera.zoom", "fx.mix",
                "view.plane.XY", "view.shape", "camera.reset"):
        assert not centred_target(reg[pid]), pid
    from hyperspace.params import Param
    assert centred_target(Param("x.a", "a", Kind.CONTINUOUS, lo=-2.0, hi=2.0))
    assert not centred_target(Param("x.b", "b", Kind.CONTINUOUS, lo=-2.0, hi=3.0))
    assert not centred_target(Param("x.c", "c", Kind.CONTINUOUS, lo=0.0, hi=0.0))
    assert not centred_target(Param("x.d", "d", Kind.CONTINUOUS, lo=-2.0, hi=2.0, log=True))
    assert not centred_target(Param("x.e", "e", Kind.TOGGLE, lo=-1.0, hi=1.0))


def test_no_target_is_refused_or_flagged(rig):
    """Rate-type params under a hand are allowed (the owner, 2026-10-04):
    every modulatable continuous param in the registry takes a learn from
    each kind of axis — nothing refused, nothing held, nothing warned
    about — and lands by the one table."""
    lrn, t = rig.learn, rig.table
    for b in list(t.routes()):
        t.remove(b)
    ps = [p for p in rig.reg if p.kind is Kind.CONTINUOUS and p.modulatable]
    ids = {p.id for p in ps}
    assert {"rot.rate.XY", "rot.rate.ZW", "fx.warp.drift", "fx.tripcolour.pulse",
            "view.speed"} <= ids and len(ps) > 150
    for p in ps:
        for centred in (True, False):
            lrn.arm(p.id)
            lrn.learn_source("hand:3", centred=centred, depth=0.3)
            assert not lrn.refused and lrn.pending is None, p.id
            b = t.owner(p.id)
            assert b is not None and lrn.last.startswith(f"learned {p.id} ← "), p.id
            push = (centred or centred_target(p)) and not p.integer
            assert (b.op, b.value) == (("push", 0.3) if push else ("position", 1.0)), p.id
            t.remove(b)


def test_the_same_axis_again_only_refreshes_the_gate_whatever_the_op(rig):
    """The target's performer is this same axis: the learn refreshes `when`
    and changes nothing else — a push row with a tuned depth (a preset's,
    or one the owner turned down on ROUTING) keeps its op and depth, and a
    position row is not turned into a push. No prompt either way."""
    lrn, t = rig.learn, rig.table
    tuned = t.add(Binding("hand:3", "view.speed", "push", 0.6, rest=0.4, scale="master.gain"))
    lrn.arm("view.speed")
    lrn.learn_source("hand:3", when="hand:14", centred=True, depth=0.25)
    assert lrn.pending is None and t.routes_to("view.speed") == [tuned]
    assert tuned == Binding("hand:3", "view.speed", "push", 0.6, rest=0.4, scale="master.gain",
                            when="hand:14")
    assert "learned view.speed ← hand 3 pushes +0.6" in lrn.last
    fader = t.add(Binding("hand:7", "rot.rate.XY", "position", 0.8))
    lrn.arm("rot.rate.XY")
    lrn.learn_source("hand:7", when="hand:15", centred=True, depth=0.25)
    assert t.routes_to("rot.rate.XY") == [fader]
    assert fader == Binding("hand:7", "rot.rate.XY", "position", 0.8, when="hand:15")
    lrn.arm("rot.rate.XY")
    lrn.learn_source("hand:7")                                 # and the gate comes off again
    assert fader.when is None and (fader.op, fader.value) == ("position", 0.8)


def test_a_learn_onto_a_performed_param_is_still_held_whatever_the_op(rig):
    """One performer per parameter: a learned push asks Replace / Keep
    exactly as a learned position did, and the table waits for the answer."""
    lrn, t = rig.learn, rig.table
    old = t.add(Binding("lfo:0", "rot.rate.XY", "push", 0.1))
    mine = t.add(Binding("hand:3", "view.bright", "push", 0.5))
    lrn.arm("rot.rate.XY")
    lrn.learn_source("hand:3", centred=True, depth=0.25)
    new, cur = lrn.pending
    assert cur is old and new == Binding("hand:3", "rot.rate.XY", "push", 0.25)
    assert "replace?" in lrn.last and t.owner("rot.rate.XY") is old
    assert t.owner("view.bright") is mine                      # nothing moved while it asks
    assert lrn.resolve_pending(False) is None and t.owner("view.bright") is mine   # Keep
    lrn.arm("rot.rate.XY")
    lrn.learn_source("hand:3", centred=True, depth=0.25)
    assert lrn.resolve_pending(True) is t.owner("rot.rate.XY")                     # Replace
    assert old not in t.bindings and mine not in t.bindings
    assert lrn.last == ("learned rot.rate.XY ← hand 3 pushes +0.25 "
                        "(into the preset; moved from view.bright)")


def test_existing_rows_are_never_rewritten(rig):
    """This is what a *new* learn lands with: rows already in the table —
    a preset's, the owner's — keep their op and depth through learns on
    other params, and a table read back from its own JSON is unchanged."""
    t = rig.table
    mine = [Binding("hand:1", "view.speed", "position", 1.0),
            Binding("hand:4", "rot.rate.XY", "position", 1.0),
            Binding("hand:5", "camera.yaw", "push", 0.5, rest=0.5),
            Binding("lfo:0", "view.bright", "push", 0.3)]
    for b in mine:
        t.add(b)
    was = [b.to_json() for b in mine]
    learned(rig, "view.inst_amp", "hand:3", centred=True, depth=0.25)
    learned(rig, "rot.rate.XW", "hand:7", depth=0.25)
    assert [b.to_json() for b in mine] == was
    assert all(any(b is x for x in t.bindings) for b in mine)
    assert [Binding.from_json(d).to_json() for d in was] == was


def test_the_two_default_depths_agree():
    """0.25 is written twice — `learn.PUSH_DEPTH` and the hands' own
    default — because hands/core.py imports nothing from the package."""
    from hyperspace.hands import HandSettings

    assert PUSH_DEPTH == HandSettings().learn_depth == 0.25


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
    """D5, D6, and plan 17 fork 6. With the global layer up a desk learn
    is refused in the same words as ever — nothing changes (the table, the
    layer, the param, the file, the preset's dot) — and now **stays
    armed**: SHIFT, pressed while it is armed, latches (an invariant
    control is no candidate; it does its own job), and the same knob then
    lands. An invariant control — a fader, SHIFT's own note, OVERDUB —
    can never be learned: a message from one is not offered to the learn,
    and the road a click takes (`learn_control`) refuses it, still armed."""
    from test_midi import cc, note, push, shift

    from hyperspace import apc40

    r = desk_rig(tmp_path)
    lib, table, lrn, reg = r.lib, r.router.table, r.learn, r.reg

    def rows():
        return [(b.to_json(), b.layer) for b in table.bindings]
    shift(r)
    assert table.layer == "global"
    before, depth4 = rows(), reg["view.depth4"].value
    lrn.arm("view.depth4", "desk")
    refusal = ("K1 (track knob 1) is on the global layer (the session's) — "
               "latch SHIFT off to learn into the preset")
    for _ in range(2):                                       # refused, and again: still armed
        push(r, cc(0x30, 90))                                # track knob 1, SHIFT on
        assert lrn.learning == "view.depth4" and lrn.want == "desk" and lrn.refused
        assert lrn.last == refusal
    assert rows() == before and table.layer == "global" and reg["view.depth4"].value == depth4
    assert not lib.is_dirty("presets") and untouched(r)
    # the invariant controls, through `learn_control` (a click's road): each
    # refused in its own words, the learn still armed, nothing bound
    for source, why in (
            (f"cc:0:{apc40.CC_MASTER}", "SM (MASTER fader) is invariant (the session's) — not learned"),
            (f"note:0:{apc40.N_SHIFT}", "⇧ (SHIFT) is invariant (the session's) — not learned"),
            (f"note:0:{apc40.N_OVERDUB}", "B11 (OVERDUB) is invariant (the session's) — not learned")):
        assert not lrn.learn_control(source, apc40)
        assert lrn.refused and lrn.last == why and lrn.learning == "view.depth4"
    assert rows() == before
    # SHIFT works through the armed learn: it latches off, and is not learned
    shift(r)
    assert table.layer == "preset" and lrn.learning == "view.depth4" and rows() == before
    # OVERDUB too: it sends the show home, as it always does
    r.reg["preset.load.2"].fire()
    loaded = lib.current("presets")
    assert loaded != lib.project.startup
    lrn.arm("view.depth4", "desk")
    before = rows()
    push(r, note(apc40.N_OVERDUB), note(apc40.N_OVERDUB, 0))
    assert lib.current("presets") == lib.project.startup and lrn.learning == "view.depth4"
    # nothing learned: depth's one desk row is the fresh layer's D1 (apc40.SCENE, plan 19 WP3)
    assert [b.source for b in table.desk() if b.target == "view.depth4" and b.is_midi] \
        == ["cc:*:16"]
    assert not lib.is_dirty("presets") and untouched(r)
    # …and after SHIFT the same knob lands, and a good learn clears the flag
    push(r, cc(0x30, 64))
    assert lrn.learning is None and lrn.want is None and not lrn.refused
    assert lrn.last.startswith("learned view.depth4 ← K1 (track knob 1) (into the preset)")
    assert [b.source for b in table.desk() if b.target == "view.depth4"] == ["cc:0:48"]
    assert lib.is_dirty("presets") and untouched(r)
    push(r, cc(0x30, 70))                                    # nothing armed: nothing more
    assert lrn.learning is None and not lrn.refused


def test_accepts_by_want():
    """Plan 17 WP2: a learn says what may complete it. `desk` accepts a
    cc / note / pitch source and no hand; `hand:left` accepts that hand's
    axes and switches by name, and not the other hand's, a number or the
    desk; None accepts anything; nothing armed accepts nothing. `arm(None)`
    and `take` clear the want."""
    from hyperspace.learn import WANTS

    lrn = Learn(NS(get=lambda pid: None), Bindings())
    desk = ("cc:0:48", "cc:*:16", "note:3:53", "pitch:0:0")
    left = ("hand:left.roll", "hand:left.pinch.index", "hand:left.present")
    other = ("hand:right.y", "hand:7", "lane:0", "lfo:1", "ext:2", "key:B")
    assert WANTS == ("desk", "hand:left", "hand:right", "pad")
    assert not any(lrn.accepts(s) for s in (*desk, *left, *other))      # nothing armed
    lrn.arm("view.bright")
    assert lrn.want is None and all(lrn.accepts(s) for s in (*desk, *left, *other))
    lrn.arm("view.bright", "desk")
    assert all(lrn.accepts(s) for s in desk)
    assert not any(lrn.accepts(s) for s in (*left, *other))
    lrn.arm("view.bright", "hand:left")
    assert all(lrn.accepts(s) for s in left)
    assert not any(lrn.accepts(s) for s in (*desk, *other, "hand:leftover.x"))
    lrn.arm("view.bright", "hand:right")
    assert lrn.accepts("hand:right.y") and not lrn.accepts("hand:left.roll")
    lrn.arm("view.bright", "pad")
    pad = ("pad:A", "hat:UP", "axis:LX", "axis:RT")
    assert all(lrn.accepts(s) for s in pad)
    assert not any(lrn.accepts(s) for s in (*desk, *left, *other))
    lrn.arm("view.bright", "desk")
    assert not any(lrn.accepts(s) for s in pad)
    lrn.arm("view.bright", "hand:right")
    lrn.learn_source("hand:left.roll")                       # the wrong hand: not taken
    assert not lrn.learn_control("cc:0:48")                  # nor the desk (review of PR #96)
    assert lrn.learning == "view.bright" and lrn.want == "hand:right"
    with pytest.raises(ValueError, match="no such want"):
        lrn.arm("view.bright", "hand:both")
    n = lrn.armed_n
    lrn.arm("view.bright", "hand:right")                     # a re-arm is a new learn
    assert lrn.armed_n == n + 1
    assert lrn.take() == "view.bright" and lrn.want is None
    lrn.arm("view.bright", "desk")
    lrn.arm(None)
    assert lrn.learning is None and lrn.want is None and not lrn.accepts("cc:0:48")
    del lrn.want                                             # a Learn from before a hot reload
    lrn.learning = "view.bright"
    assert lrn.accepts("hand:7") and lrn.accepts("cc:0:48")


def test_learn_control_needs_no_adapter(tmp_path):
    """Fork 7: the desk learn is the learn object's. A bare `Learn` over a
    table — no MidiIO anywhere — and `learn_control("cc:*:18", apc40)`: a
    preset-layer ring row, the table's `redraw_serial` bumped (an adapter,
    if there is one, redraws), one undo step, no file. The op comes from
    the profile and the param; with no profile, a plain `abs` row in the
    row's own words. The param's old knob lets go, and is named."""
    from test_undo import boot, labels, settle

    from hyperspace import apc40

    r = boot(tmp_path / "home")
    table = r.table
    lrn = Learn(r.reg, table)                                # not the adapter's
    r.undo.clear()
    assert not lrn.learn_control("cc:*:18", apc40)           # nothing armed: nothing
    on_disk = table.path.read_bytes() if table.path.exists() else None
    serial, desk_serial = table.redraw_serial, table.desk_serial
    lrn.arm("view.depth4", "desk")
    assert lrn.learn_control("cc:*:18", apc40)
    (row,) = [b for b in table.desk() if b.target == "view.depth4"]
    assert (row.source, row.op, row.layer, row.feedback, row.ring) \
        == ("cc:*:18", "abs", "preset", "ring", apc40.RING_VOLUME)
    assert table.redraw_serial > serial and table.desk_serial == desk_serial
    assert lrn.learning is None and not lrn.refused
    # its old knob lets go and is named: D1, the fresh layer's (apc40.SCENE, plan 19 WP3)
    assert lrn.last == "learned view.depth4 ← D3 (device knob 3) (into the preset); D1 let go"
    assert (table.path.read_bytes() if table.path.exists() else None) == on_disk
    settle(r)
    assert labels(r) == ["learn view.depth4"]
    assert r.undo.undo()                                     # back on D1 alone
    assert [b.source for b in table.desk() if b.target == "view.depth4"] == ["cc:*:16"]
    # the param's knob moves to another control: the old one lets go, by glyph
    assert [b.source for b in table.desk() if b.target == "view.bright" and b.kind == "cc"] \
        == ["cc:0:48"]
    lrn.arm("view.bright", "desk")
    assert lrn.learn_control("cc:0:19", apc40)
    assert lrn.last == "learned view.bright ← D4 (device knob 4) (into the preset); K1 let go"
    assert [b.source for b in table.desk() if b.target == "view.bright" and b.kind == "cc"] \
        == ["cc:0:19"]
    # the op: a note is a toggle with an LED, the cue knob is relative, a
    # knob on a trigger is a toggle; no profile is a plain row
    lrn.arm("view.lines", "desk")
    pad = f"note:3:{apc40.N_CLIP[2]}"                        # clip row 3, track 4
    assert lrn.learn_control(pad, apc40)
    row = next(b for b in table.desk() if b.target == "view.lines" and b.source == pad)
    assert (row.op, row.feedback, row.on) == ("toggle", "led", apc40.GREEN)
    lrn.arm("view.instances", "desk")
    assert lrn.learn_control(f"cc:0:{apc40.CC_CUE}", apc40)
    assert next(b for b in table.desk() if b.target == "view.instances"
                and b.number == apc40.CC_CUE).op == "rel"
    lrn.arm("view.speed", "desk")
    assert lrn.learn_control("cc:0:20")
    row = next(b for b in table.desk() if b.source == "cc:0:20")
    assert (row.target, row.op, row.feedback) == ("view.speed", "abs", None)
    assert lrn.last.startswith("learned view.speed ← MIDI CC 20 ch1 (into the preset)")
    # a learn armed for a hand is not the desk's to complete… by the adapter
    # (`MidiIO._handle` asks `accepts`); an id the registry lacks never lands
    lrn.arm("no.such.param", "desk")
    assert not lrn.learn_control("cc:0:21", apc40) and lrn.learning is None


# ------------------------------------------------------ plan 15 WP1: undo

def test_a_learn_is_one_undo_step(tmp_path):
    """A learn landing is one undo step, by either adapter: a hand's (the
    axis's other row and the target's old owner go with it, and come back
    whole), the prompt's Replace, and a knob's desk row. Undoing it is a
    restore, not a load: `desk_serial` does not move."""
    from test_undo import boot, cc, frames, labels, settle

    r = boot(tmp_path / "home")
    reg, table, lrn, u = r.reg, r.table, r.learn, r.undo

    def routes():
        return [b.to_json() for b in table.routes()]

    def desk():
        return [b.to_json() for b in table.desk()]
    table.set_routes([Binding("hand:3", "view.inst_amp", "position"),
                      Binding("hand:3", "view.depth4", "push", 0.4, when="hand:14"),
                      Binding("lfo:0", "view.bright", "push", 0.3)])
    settle(r)
    u.clear()
    was = routes()
    # a hand learn: the axis moves to the new param — its old rows go, the
    # position and the push (plan 18 fork 7), and one ⌘Z brings both back
    lrn.arm("view.speed")
    lrn.learn_source("hand:3")
    assert table.owner("view.speed").source == "hand:3" and table.owner("view.inst_amp") is None
    assert table.owner("view.depth4") is None
    assert lrn.last.endswith("(into the preset; moved from view.inst_amp, view.depth4)")
    settle(r)
    assert labels(r) == ["learn view.speed"]
    assert u.undo() and routes() == was and u.status == "undid learn view.speed"
    assert u.redo() and table.owner("view.speed").source == "hand:3"
    assert u.undo() and routes() == was
    # a taken target asks; Replace is the step, and the old owner comes back
    frames(r, 3)
    lrn.arm("view.bright")
    lrn.learn_source("hand:7")
    assert lrn.pending is not None
    settle(r)
    assert u.stack == []                                     # a question changes nothing
    lrn.resolve_pending(True)
    settle(r)
    assert labels(r) == ["learn view.bright"] and table.owner("view.bright").source == "hand:7"
    assert u.undo() and routes() == was
    # the same axis again onto the same param only refreshes the gate: a step too
    frames(r, 3)
    lrn.arm("view.inst_amp")
    lrn.learn_source("hand:3", when="hand:18")
    settle(r)
    assert table.owner("view.inst_amp").when == "hand:18" and len(u.stack) == 1
    assert u.undo() and routes() == was
    # a knob learn: a desk row of the preset's, taking the control's old row
    frames(r, 3)
    knob = next(b for b in table.desk() if b.kind == "cc" and b.op == "abs")
    target = next(p.id for p in reg if p.group == "view" and p.id != knob.target
                  and not any(b.target == p.id for b in table.midi()))
    before, serial = desk(), table.desk_serial
    lrn.arm(target)
    r.inp.queue.append(cc(knob.number, 64, knob.channel or 0))
    frames(r)
    assert "learned" in lrn.last and desk() != before
    settle(r)
    assert labels(r) == [f"learn {target}"]
    assert u.undo() and desk() == before and table.desk_serial == serial
    assert u.redo() and any(b.target == target for b in table.desk())


# ------------------------------------------------------ plan 17 WP1: one Unbind

def bound_rig(home):
    """The app's construction with the undo (tests/test_undo.boot: TUMBLE
    loaded), and on Brightness — a knob and two step buttons in that preset
    — a hand route, a disabled LFO route with a macro on its depth, and an
    invariant row of the session's."""
    from test_undo import boot, settle

    from hyperspace.routing import Macro, Sub

    r = boot(home)
    table = r.table
    pid = r.pid = "view.bright"
    assert {b.kind for b in table.desk() if b.target == pid} == {"cc", "note"}
    assert len([b for b in table.desk() if b.target == pid]) == 3 and not table.routes_to(pid)
    table.add(Binding("hand:right.y", pid, "position"))
    table.add(Binding("lfo:0", pid, "push", 0.3, enabled=False))
    table.macros["macro.1"] = Macro("Wobble", [Sub(depth=("lfo:0", pid), lo=0.0, hi=0.6)])
    r.session = Binding("cc:0:119", pid, "abs")              # no layer: invariant
    table.bindings.append(r.session)
    table.write()
    settle(r)
    r.undo.clear()
    r.on_disk = (table.path.read_text(), table.path.stat().st_mtime_ns)
    r.path = table.path
    return r


def left(table, pid) -> list:
    """The MIDI rows and routes still on a param."""
    return [b for b in table.bindings
            if b.target == pid and (b.is_midi or any(b is x for x in table.routes()))]


def test_unbind_removes_the_presets_desk_rows_and_every_route(tmp_path):
    """Plan 17 WP1, fork 4: one Unbind removes what is bound to the param
    in the loaded preset — its knob, its two step buttons, the hand route
    and the disabled LFO route (its depth subscriber with it) — and never
    a session row. The preset is dirty; no file is written. It needs no
    MIDI adapter: the call is the learn object's."""
    r = bound_rig(tmp_path / "home")
    table, lrn, pid = r.table, r.learn, r.pid
    serial = table.redraw_serial
    desk, routes, session = lrn.bound((pid,))
    assert len(desk) == 3 and [b.scheme for b in routes] == ["hand", "lfo"]
    assert session == [r.session]
    gone = lrn.unbind((pid, pid))                            # an id given twice is one id
    assert len(gone) == 5 and not lrn.refused
    assert left(table, pid) == [r.session]                   # the keys' rows are not Unbind's
    assert table.redraw_serial > serial                      # an adapter redraws: dark (D8)
    assert not table.depth_subs(routes[1]) and not table.macros["macro.1"].subs
    assert lrn.last.startswith(f"unbound {pid} from ") and " and LFO" not in lrn.last
    assert lrn.last.count(",") == 3 and " and " in lrn.last  # five rows named
    assert r.lib.is_dirty("presets") and untouched(r)
    # a bare Learn over a table, no registry rule, no adapter: the same
    t = Bindings([Binding("cc:0:48", "a", "abs", layer="preset"), Binding("lane:1", "a", "push"),
                  Binding("cc:0:7", "a", "abs")])
    bare = Learn(r.reg, t)
    assert len(bare.unbind("a", name=lambda b: b.source.upper())) == 2
    assert bare.last == "unbound a from CC:0:48 and LANE:1"
    assert [b.source for b in t.bindings] == ["cc:0:7"]
    # only the session's row left: a refusal, in the words Unbind always used
    assert bare.unbind("a") == [] and bare.refused
    assert bare.last == ("MIDI CC 7 ch1 → a is invariant (the session's, edited in "
                         "bindings.json) — not unbound")
    assert bare.unbind("nothing.here") == [] and bare.unbind(()) == []


def test_unbind_by_kind(tmp_path):
    """`desk=False` leaves the desk rows; `routes=False` leaves the routes;
    an alias's routes are its band's (the drawn id and the real one)."""
    r = bound_rig(tmp_path / "home")
    table, lrn, pid = r.table, r.learn, r.pid
    gone = lrn.unbind((pid,), desk=False)
    assert [b.scheme for b in gone] == ["hand", "lfo"] and not table.routes_to(pid)
    assert len([b for b in table.desk() if b.target == pid]) == 3
    assert lrn.unbind((pid,), desk=False) == [] and not lrn.refused   # nothing: said nothing
    table.add(Binding("hand:left.x", pid, "position"))
    gone = lrn.unbind((pid,), routes=False)
    assert len(gone) == 3 and all(b.is_midi for b in gone)
    assert [b.source for b in table.routes_to(pid)] == ["hand:left.x"]
    assert not [b for b in table.desk() if b.target == pid]
    # the drawn alias and its band: the desk row on the alias, the route on the band
    r.control.selb = 2
    table.bindings.append(Binding("cc:0:20", "band.sel.thr", "abs", layer="preset"))
    table.add(Binding("lane:0", "band.2.thr", "push", 0.2))
    gone = lrn.unbind(("band.sel.thr", "band.2.thr"))
    assert {b.target for b in gone} >= {"band.sel.thr", "band.2.thr"}
    assert not table.routes_to("band.2.thr")
    assert not [b for b in table.desk() if b.target == "band.sel.thr"]
    assert lrn.last.startswith("unbound band.2.thr from ")
    # a MIDI row is never a "route", whatever its op (review of PR #93): a
    # session row with a performer op stays, and is a refusal, not an item
    odd = Binding("cc:0:118", "view.zoom_rate", "push")           # no layer: the session's
    mine = Binding("cc:0:117", "view.zoom_rate", "position", layer="preset")
    table.bindings += [odd, mine]
    assert lrn.bound("view.zoom_rate") == ([mine], [], [odd])
    assert lrn.unbind("view.zoom_rate", desk=False) == []
    assert lrn.unbind("view.zoom_rate") == [mine] and lrn.last.count("MIDI CC 117") == 1
    assert lrn.unbind("view.zoom_rate") == [] and lrn.refused and odd in table.bindings
    # a question held against a route that Unbind removes is withdrawn
    old = table.add(Binding("hand:left.y", "view.inst_amp", "position"))
    lrn.arm("view.inst_amp")
    lrn.learn_source("hand:right.y")
    assert lrn.pending is not None and lrn.pending[1] is old
    assert lrn.unbind("view.inst_amp", desk=False) == [old] and lrn.pending is None


def test_unbind_is_one_undo_step_and_none_when_nothing_goes(tmp_path):
    """One Ctrl+Z puts every row back, a route's depth subscriber with it;
    an unbind that removes nothing (a refusal, a free param) pushes no
    step at all."""
    from test_undo import frames, labels, settle

    r = bound_rig(tmp_path / "home")
    table, lrn, u, pid = r.table, r.learn, r.undo, r.pid

    def state():
        return ([(b.to_json(), b.layer) for b in table.bindings],
                json.dumps(table.macros_doc(), sort_keys=True))
    was = state()
    assert len(lrn.unbind((pid,))) == 5 and state() != was
    assert len(u.stack) == 1                                 # pushed once, at the call
    settle(r)
    assert labels(r) == [f"unbind {pid}"]
    assert u.undo() and u.status == f"undid unbind {pid}"
    assert sorted(map(str, state()[0])) == sorted(map(str, was[0])) and state()[1] == was[1]
    assert u.redo() and left(table, pid) == [r.session]
    assert u.undo()
    frames(r, 3)
    # by kind: still one step each
    lrn.unbind((pid,), routes=False)
    settle(r)
    assert labels(r) == [f"unbind {pid}"] and u.undo()
    frames(r, 3)
    # nothing goes: no push — the stack does not grow even before it settles
    lrn.unbind(("output.dim",))                              # the crossfader's: the session's
    assert lrn.refused and "invariant" in lrn.last and u.stack == []
    free = next(p.id for p in r.reg if not any(b.target == p.id for b in table.bindings))
    lrn.unbind((free,))
    assert u.stack == []
    settle(r)
    assert u.stack == [] and len(u.redos) == 1               # and the redo is not spent


# ------------------------------------------------ plan 17 WP4: click a control, then a param

def test_pick_then_param_maps_through_the_learn(tmp_path):
    """`pick("cc:*:18")`, `map_picked("view.speed", apc40)`: the row
    `learn_control` makes — one mapping path — the param's old knob row
    gone and named in the message, one Ctrl+Z restoring both, no file
    written. A pick is no undo step and changes no table; arming a param
    lets the pick go, picking a control cancels an armed learn."""
    from test_undo import boot, labels, settle

    from hyperspace import apc40

    r = boot(tmp_path / "home")
    table, lrn, u = r.table, r.learn, r.undo

    def desk():
        return [b.to_json() for b in table.desk()]
    settle(r)
    u.clear()
    on_disk = table.path.read_bytes() if table.path.exists() else None
    assert [b.source for b in table.desk() if b.target == "view.speed" and b.kind == "cc"] \
        == ["cc:0:49"]                                       # K2 has Speed in the startup preset
    before, serial = desk(), table.redraw_serial
    assert lrn.control is None and not lrn.map_picked("view.speed", apc40)   # nothing picked
    lrn.pick("cc:*:18")                                      # D3
    assert lrn.control == "cc:*:18" and lrn.learning is None
    settle(r)
    assert desk() == before and labels(r) == [] and table.redraw_serial == serial
    assert lrn.map_picked("view.speed", apc40)
    assert lrn.control is None and lrn.learning is None and not lrn.refused
    (row,) = [b for b in table.desk() if b.target == "view.speed" and b.kind == "cc"]
    assert (row.source, row.op, row.layer, row.feedback, row.ring) \
        == ("cc:*:18", "abs", "preset", "ring", apc40.RING_VOLUME)
    assert lrn.last == "learned view.speed ← D3 (device knob 3) (into the preset); K2 let go"
    assert table.redraw_serial > serial                      # an adapter would redraw the desk
    assert (table.path.read_bytes() if table.path.exists() else None) == on_disk
    assert r.lib.is_dirty("presets")                         # the loaded preset's edit: its dot
    mapped = desk()
    settle(r)
    assert labels(r) == ["learn view.speed"]                 # one step…
    assert u.undo() and desk() == before                     # …and both rows are back
    # the same row the knob learn's road makes
    lrn.arm("view.speed", "desk")
    assert lrn.learn_control("cc:*:18", apc40) and desk() == mapped
    # a pick and an armed learn never stand together
    lrn.pick("cc:*:19")
    lrn.arm("view.bright", "desk")
    assert lrn.control is None and lrn.learning == "view.bright"
    lrn.pick("cc:*:19")
    assert lrn.control == "cc:*:19" and lrn.learning is None and lrn.want is None
    lrn.pick(None)
    assert lrn.control is None
    # a param the registry lacks: nothing lands, nothing is left armed, and
    # it says so — the control still picked
    lrn.pick("cc:*:19")
    assert not lrn.map_picked("no.such.param", apc40) and lrn.learning is None
    assert lrn.control == "cc:*:19" and lrn.refused
    assert lrn.last == "no.such.param: no such param — nothing mapped"


def test_a_pick_on_an_invariant_control_or_the_global_layer_maps_nothing(tmp_path):
    """D5, D6: `ui_desk.mappable` gives the reason before the click, and
    `map_picked` refuses in the knob learn's words — the table untouched,
    no undo step, no learn left armed, the control still picked."""
    from test_undo import boot, labels, settle

    from hyperspace import apc40, learn, ui_desk

    r = boot(tmp_path / "home")
    table, lrn, u = r.table, r.learn, r.undo

    def rows():
        return [(b.to_json(), b.layer) for b in table.bindings]

    def control(glyph):
        return next(c for c in apc40.LAYOUT if c.glyph == glyph)
    settle(r)
    u.clear()
    before = rows()
    # MASTER: the track faders are layered since plan 24 C2 (decision 17)
    s3 = control("SM")
    # one rule, asked before the click and refused by after it (`learn.blocked`)
    assert learn.blocked(table, s3.source) == "invariant"
    assert learn.blocked(table, "cc:0:48") is None
    assert ui_desk.mappable(table, s3) == "SM (MASTER fader) is invariant (the session's)"
    lrn.pick(s3.source)
    assert not lrn.map_picked("view.speed", apc40)
    assert lrn.refused and lrn.last == "SM (MASTER fader) is invariant (the session's) — not learned"
    assert lrn.control == s3.source and lrn.learning is None and rows() == before
    # every invariant control of D6: MASTER (S1–S8 are layered since plan 24
    # C2), the bank row, SHIFT, TAP,
    # METRONOME, NUDGE, the transport, the crossfader, OVERDUB (the clip-stop
    # row is free since 2026-10-09);
    # and since plan 19 WP2 clip rows 4 and 5, the bank's slots 9–24
    for glyph in ("SM", "G1·1", "G1·8", "⇧", "B20", "B12", "B21", "B22", "B13", "B14",
                  "X", "B11", "G4·1", "G5·8"):
        c = control(glyph)
        assert "is invariant (the session's)" in (ui_desk.mappable(table, c) or ""), glyph
        lrn.pick(c.source)
        assert not lrn.map_picked("view.speed", apc40) and lrn.refused, glyph
    assert rows() == before
    # the global layer: nothing is mapped while it is up, a free knob included
    k1, k6 = control("K1"), control("K6")
    assert ui_desk.mappable(table, k1) is None and ui_desk.mappable(table, k6) is None
    table.set_layer("global")
    assert learn.blocked(table, k1.source) == "global"
    assert learn.blocked(table, s3.source) == "invariant"       # invariant on both layers
    assert ui_desk.mappable(table, k1) == (
        "K1 (track knob 1) is on the global layer (the session's) — latch SHIFT off to map "
        "into the preset")
    assert ui_desk.mappable(table, k6) is not None
    lrn.pick(k1.source)
    assert not lrn.map_picked("view.depth4", apc40)
    assert lrn.refused and lrn.last == (
        "K1 (track knob 1) is on the global layer (the session's) — latch SHIFT off to learn "
        "into the preset")
    assert lrn.control == k1.source and lrn.learning is None and rows() == before
    settle(r)
    assert labels(r) == []
    # SHIFT off: the same pick lands
    table.set_layer("preset")
    assert lrn.map_picked("view.depth4", apc40) and lrn.control is None
    assert [b.source for b in table.desk() if b.target == "view.depth4" and b.kind == "cc"] \
        == [k1.source]


def test_a_hand_learn_onto_a_setting_is_refused_in_words(rig):
    """Plan 21 R12: `ghost.mirror`, `.guide`, `.tethers` and `.style` are
    not modulatable. A hand completing a learn armed on one (the panel
    never offers Learn hand there; a bare arm can still get here) makes no
    row, holds no question, ends the learn and says why in a line the
    performer can read; a modulatable ghost param still learns."""
    lrn, t = rig.learn, rig.table
    for pid in ("ghost.mirror", "ghost.guide", "ghost.tethers", "ghost.style"):
        n = len(t.bindings)
        lrn.arm(pid, "hand:right")
        lrn.learn_source("hand:right.x")
        assert lrn.refused and lrn.pending is None and lrn.learning is None, pid
        assert t.owner(pid) is None and len(t.bindings) == n, pid
        label = rig.reg[pid].label
        assert lrn.last == (f"{label} can't follow a hand (not modulatable) — not learned; "
                            "Learn desk puts it on a button"), pid
    lrn.arm("ghost.alpha", "hand:right")
    lrn.learn_source("hand:right.y")
    assert not lrn.refused and t.owner("ghost.alpha").source == "hand:right.y"
