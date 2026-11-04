"""The base chase (plan 52): while held, the performer is committed into the
base; let go, the look stays where the performer left it.

The param model first, against a twin the verb never touches (what shows is
what would have shown), then the rig: the real router's rows, undo's one step
per hold, the dirty dot, the projector's hold, Learn, and two decks over one
session."""

from __future__ import annotations

import math
import random
from types import SimpleNamespace

import mido
import pytest
from test_undo import boot, frames, labels

from hyperspace import hold as H
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.control import Control
from hyperspace.params import (
    CHASE_LABEL,
    CHASE_PARAM,
    Registry,
    build_performance,
    build_session,
    chase_reaches,
)
from hyperspace.routing import Binding
from hyperspace.tapers import T_DRIVE
from hyperspace.undo import SETTLE_S
from hyperspace.view import ViewState


def declare(r: Registry, pid: str, v: float = 0.5, **kw):
    """A continuous param of the look's over a one-cell object."""
    cell = [v]
    kw.setdefault("group", "view")
    return r.continuous(pid, pid, lambda: cell[0], lambda x: cell.__setitem__(0, x), **kw)


def land(p, push: float = 0.0, pos: float | None = None, mark=None) -> None:
    """One frame of this param's sources, then its landing."""
    p.modulate(push)
    if pos is not None:
        p.modulate(pos - p.norm, position=True)
    p.apply(mark)


@pytest.fixture()
def reg():
    return Registry()


# ---------------------------------------------------------------- the verb

def test_what_shows_goes_into_the_base_and_stays(reg):
    p = declare(reg, "view.a", 0.5)
    land(p, 0.2)
    assert p.value == pytest.approx(0.7) and p.base == pytest.approx(0.5)
    reg.base_chase(True)
    land(p, 0.2)
    assert p.value == pytest.approx(0.7), "the press moves nothing"
    assert p.base == pytest.approx(0.7), "and the base holds what shows"
    land(p, 0.3)
    assert p.value == pytest.approx(0.8) and p.base == pytest.approx(0.8)
    reg.base_chase(False)
    land(p, 0.3)
    assert p.value == pytest.approx(0.8) and p.base == pytest.approx(0.8), "no jump at the release"


def test_a_source_going_home_after_the_release_moves_nothing(reg):
    p = declare(reg, "view.a", 0.5)
    reg.base_chase(True)
    land(p, 0.3)
    reg.base_chase(False)
    for off in (0.3, 0.2, 0.1, 0.0):
        land(p, off)
        assert p.value == pytest.approx(0.8), off
    # home: the route rides the new base in full, nothing left in the ledger
    assert p._trim == 0.0
    land(p, 0.1)
    assert p.value == pytest.approx(0.9)
    land(p, -0.2)
    assert p.value == pytest.approx(0.6)
    assert p.base == pytest.approx(0.8), "and the base is the committed value throughout"


def test_a_source_pushing_further_moves_on_from_where_the_look_stands(reg):
    p = declare(reg, "view.a", 0.2)
    reg.base_chase(True)
    land(p, 0.3)
    reg.base_chase(False)
    land(p, 0.4)
    assert p.value == pytest.approx(0.6)       # 0.5 committed, 0.1 further
    land(p, 0.35)
    assert p.value == pytest.approx(0.55)      # back toward where it was let go
    land(p, 0.2)
    assert p.value == pytest.approx(0.5), "below the commit point the look holds"
    land(p, 0.3)
    assert p.value == pytest.approx(0.6), "the ledger fell with it: 0.2 is the new zero"


def test_a_negative_offset_is_the_same_rule(reg):
    p = declare(reg, "view.a", 0.5)
    reg.base_chase(True)
    land(p, -0.3)
    reg.base_chase(False)
    assert p.base == pytest.approx(0.2)
    land(p, -0.1)
    assert p.value == pytest.approx(0.2)
    land(p, 0.1)                               # past zero: rides in full
    assert p.value == pytest.approx(0.3)


def test_the_source_leaving_keeps_the_commit(reg):
    p = declare(reg, "view.a", 0.5)
    reg.base_chase(True)
    land(p, 0.3)
    reg.base_chase(False)
    p.apply()                                  # nothing called: the source is gone
    assert not p.modulated and p.value == pytest.approx(0.8)
    land(p, 0.1)
    assert p.value == pytest.approx(0.9), "a source back later rides it in full"


SWEEP = [{}, {"wrap": True}, {"lo": 1.0, "hi": 100.0, "log": True}, {"taper": T_DRIVE},
         {"lo": 0.0, "hi": 20.0, "integer": True}]


@pytest.mark.parametrize("kw", SWEEP, ids=["plain", "wrap", "log", "taper", "integer"])
def test_while_held_it_shows_what_it_would_have_shown(reg, kw):
    """The press and the whole hold are invisible: a twin nobody chases shows
    the same every frame, past the range's ends too."""
    rnd = random.Random(52)
    v = kw.get("lo", 0.0) + (kw.get("hi", 1.0) - kw.get("lo", 0.0)) / 3 if "taper" not in kw else 2.0
    a, b = declare(reg, "view.a", v, **kw), declare(reg, "view.b", v, **kw)
    for held in (False, True):
        if held:
            reg.base_chase(True)
            b._chase = False                   # the twin is out of the verb's reach
        off = 0.0
        for _ in range(300):
            off = max(-1.5, min(1.5, off + rnd.uniform(-0.1, 0.1)))
            land(a, off)
            land(b, off)
            assert a.value == pytest.approx(b.value, abs=1e-6)
            if held:
                assert a.base == pytest.approx(a.value, abs=1e-6)


def test_no_jump_at_any_release_of_a_swinging_source(reg):
    """An LFO's swing, let go anywhere: the frame after moves by no more than
    the source itself moved, and the base is what it showed."""
    p = declare(reg, "view.a", 0.5)
    for k in range(40):
        w = [0.2 * math.sin(i * 0.3 + k) for i in range(30)]
        reg.base_chase(True)
        for off in w[:15]:
            land(p, off)
        shown = p.value
        reg.base_chase(False)
        assert p.base == pytest.approx(shown)
        prev = shown
        for i, off in enumerate(w[15:]):
            land(p, off)
            assert abs(p.value - prev) <= abs(off - w[14 + i]) + 1e-9
            prev = p.value
        p.apply()                              # let go, the next round starts clean
        p.set(0.5)


def test_a_range_end_does_not_eat_the_way_back(reg):
    p = declare(reg, "view.a", 0.5)
    reg.base_chase(True)
    land(p, 0.8)                               # 1.3 cut off at 1
    assert p.value == 1.0 and p.base == 1.0
    land(p, 0.6)                               # 1.1, cut off still: with no verb it reads 1
    assert p.value == 1.0
    land(p, 0.4)
    assert p.value == pytest.approx(0.9)
    land(p, 0.8)
    reg.base_chase(False)
    land(p, 0.8)
    assert p.value == 1.0, "no jump at the end stop either"
    land(p, 0.6)
    land(p, 0.3)
    assert p.value == 1.0, "and going home it holds"


def test_a_fader_row_lands_what_it_says_and_its_last_value_stays(reg):
    p = declare(reg, "view.a", 0.5)
    reg.base_chase(True)
    land(p, pos=0.2)
    assert p.value == pytest.approx(0.2) and p.base == pytest.approx(0.2)
    land(p, pos=0.3)
    assert p.value == pytest.approx(0.3) and p.base == pytest.approx(0.3)
    reg.base_chase(False)
    assert p._trim == pytest.approx(0.0)
    land(p, pos=0.3)
    assert p.value == pytest.approx(0.3)
    land(p, pos=0.6)
    assert p.value == pytest.approx(0.6), "the row is still the fader"
    assert p.base == pytest.approx(0.3)
    p.apply()                                  # the row gone: the committed value
    assert p.value == pytest.approx(0.3)


def test_a_push_beside_a_fader_row_is_not_counted_twice(reg):
    p = declare(reg, "view.a", 0.5)
    reg.base_chase(True)
    land(p, 0.1, pos=0.3)
    assert p.value == pytest.approx(0.4) and p.base == pytest.approx(0.4)
    land(p, 0.2, pos=0.3)
    assert p.value == pytest.approx(0.5) and p.base == pytest.approx(0.5)
    reg.base_chase(False)
    land(p, 0.2, pos=0.3)
    assert p.value == pytest.approx(0.5)
    land(p, 0.2)                               # the fader row goes: the push alone
    assert p.value == pytest.approx(0.5), "the base already holds the push"


def test_a_knob_turned_under_the_verb_moves_the_base_and_the_look(reg):
    p = declare(reg, "view.a", 0.5)
    reg.base_chase(True)
    land(p, 0.1)
    p.set(0.3)
    land(p, 0.1)
    assert p.value == pytest.approx(0.3) and p.base == pytest.approx(0.3)


def test_a_landed_value_rides_in_full(reg):
    """`Registry.restore`, the road of a load and of an undo: the value says
    what the base is, the route on top as if nothing had been committed."""
    p = declare(reg, "view.a", 0.2)
    reg.base_chase(True)
    land(p, 0.3)
    reg.base_chase(False)
    reg.restore({"view.a": 0.2})
    land(p, 0.3)
    assert p.value == pytest.approx(0.5) and p.base == pytest.approx(0.2)


# ---------------------------------------------------------------- the reach

def test_the_verb_reaches_continuous_modulatable_look_params():
    chain = Analyzer(Analyser())
    session = build_session(Control(chain), SimpleNamespace(chain=chain))
    reg = build_performance(ViewState(), session=session)
    reached = {p.id for p in reg if chase_reaches(p)}
    assert "view.bright" in reached and "rot.rate.XY" in reached and "camera.yaw" in reached
    for p in reg:
        if p.id in reached:
            assert p.modulatable and p.kind.value == "continuous"
    assert "master.gain" not in reached, "a session param is the room's"
    assert not any(p.id in reached for p in session)
    reg["macro.1"]                             # declared
    assert not any(i.startswith("macro.") for i in reached), "a macro's base moves its subscribers"
    assert CHASE_PARAM not in reached and not reg[CHASE_PARAM].persist
    assert CHASE_PARAM not in session, "every deck has its own"


def test_two_decks_chase_alone_and_leave_the_session_alone():
    chain = Analyzer(Analyser())
    session = build_session(Control(chain), SimpleNamespace(chain=chain))
    a = build_performance(ViewState(), session=session)
    b = build_performance(ViewState(), session=session)
    a[CHASE_PARAM].set(True)
    assert a.chasing and not b.chasing and not b[CHASE_PARAM].value
    pa, pb = a["view.bright"], b["view.bright"]
    was_a, was_b = pa.base, pb.base
    m = session["master.gain"]
    gain = m.base
    for q in (pa, pb, m):
        q.modulate(0.05)
        q.apply()
    assert pa.base != pytest.approx(was_a), "this deck's look took it"
    assert pb.base == pytest.approx(was_b), "the other deck's did not"
    assert m.base == pytest.approx(gain), "nor the room's"


def test_a_param_declared_under_the_verb_is_reached(reg):
    reg.base_chase(True)
    p = declare(reg, "view.late", 0.5)
    land(p, 0.1)
    assert p.base == pytest.approx(0.6)
    q = declare(reg, "master.late", 0.5, group="master")
    land(q, 0.1)
    assert q.base == pytest.approx(0.5)
    reg.base_chase(False)
    assert not p._chase


def test_an_untouched_path_lands_as_it_did(reg):
    """No verb ever held: no ledger on the road."""
    p = declare(reg, "view.a", 0.5)
    land(p, 0.2)
    assert p._trim == 0.0 and p._pos is None and not p._chase
    assert p.value == 0.5 + 0.2 and p.base == 0.5
    p.apply()
    assert p.value == 0.5 and not p.modulated


# ---------------------------------------------------------------- the rig

@pytest.fixture()
def rig(tmp_path):
    return boot(tmp_path / "home")


def routed(r, pid="view.bright"):
    """A hand axis pushing `pid` as the real router drives it. `out` is its
    reading (rests at 0.5); the frame loop feeds it."""
    for row in r.table.routes_to(pid):
        r.table.remove(row)
    r.table.add(Binding("hand:0", pid, "push", 1.0, rest=0.5))
    r.out_value = [0.5]
    settle_with(r)
    r.undo.clear()
    return r.reg[pid]


def feed(r):
    return lambda _t: [r.out_value[0]] * 16


def go(r, n=1):
    frames(r, n, hand=feed(r))


def settle_with(r):
    go(r, int(SETTLE_S * 60) + 5)


def test_the_real_router_commits_and_nothing_jumps(rig):
    p = routed(rig)
    start = p.base
    rig.out_value[0] = 0.6
    go(rig, 2)
    shown = p.value
    assert shown != pytest.approx(start)
    rig.reg[CHASE_PARAM].set(True)
    go(rig, 2)
    assert p.value == pytest.approx(shown) and p.base == pytest.approx(shown)
    rig.reg[CHASE_PARAM].set(False)
    go(rig, 2)
    assert p.value == pytest.approx(shown)
    rig.out_value[0] = 0.5                     # the hand comes back to rest
    go(rig, 3)
    assert p.value == pytest.approx(shown) and p.base == pytest.approx(shown)
    assert rig.table.routes()[-1].value == 1.0, "the route's depth is the depth it was"


def test_one_hold_is_one_undo_step_however_still_it_goes(rig):
    p = routed(rig)
    start = p.base
    rig.reg[CHASE_PARAM].set(True)
    for off in (0.6, 0.65, 0.65):
        rig.out_value[0] = off
        go(rig, 2)
        settle_with(rig)                       # quiet well past the settle time, still held
    assert len(rig.undo.stack) == 1
    rig.reg[CHASE_PARAM].set(False)
    assert labels(rig) == [CHASE_LABEL]
    moved = p.base
    assert moved != pytest.approx(start)
    # a second hold is a second step
    rig.reg[CHASE_PARAM].set(True)
    rig.out_value[0] = 0.7
    go(rig, 2)
    rig.reg[CHASE_PARAM].set(False)
    assert labels(rig) == [CHASE_LABEL, CHASE_LABEL]
    rig.out_value[0] = 0.5
    settle_with(rig)
    assert labels(rig) == [CHASE_LABEL, CHASE_LABEL], "a release settles nothing more"
    assert rig.undo.undo()
    assert p.base == pytest.approx(moved)
    assert rig.undo.undo()
    assert p.base == pytest.approx(start)
    go(rig, 3)
    assert p.value == pytest.approx(start)
    assert rig.undo.redo()
    assert p.base == pytest.approx(moved)


def test_undo_with_the_source_still_out_shows_what_it_would_have(rig):
    p = routed(rig)
    start = p.base
    rig.out_value[0] = 0.6
    go(rig, 2)
    shown = p.value
    rig.reg[CHASE_PARAM].set(True)
    go(rig, 2)
    rig.reg[CHASE_PARAM].set(False)
    assert rig.undo.undo()
    go(rig, 2)
    assert p.base == pytest.approx(start)
    assert p.value == pytest.approx(shown), "as if the verb had never been held"


def test_a_hold_that_moved_nothing_costs_no_step_and_no_dirty_dot(rig):
    routed(rig)
    dirty = rig.presets.is_dirty()
    rig.undo.clear()
    rig.reg[CHASE_PARAM].set(True)
    go(rig, 5)                                 # the hand at rest: nothing to commit
    rig.reg[CHASE_PARAM].set(False)
    assert labels(rig) == []
    assert rig.presets.is_dirty() == dirty


def test_a_commit_lights_the_dirty_dot_and_a_save_holds_it(rig):
    p = routed(rig)
    rig.presets.save_as("CHASED")
    assert not rig.presets.is_dirty()
    rig.out_value[0] = 0.6
    go(rig, 2)
    assert not rig.presets.is_dirty(), "an offset alone is no edit"
    rig.reg[CHASE_PARAM].set(True)
    go(rig, 2)
    rig.reg[CHASE_PARAM].set(False)
    assert rig.presets.is_dirty()
    assert rig.reg.snapshot(part="performance")[p.id] == pytest.approx(p.value)


def test_the_turn_commits_with_no_step(rig):
    """`rot.phase.*` is no base to undo (the pose): a route on it commits and
    stays, and costs the stack nothing."""
    p = routed(rig, "rot.phase.XY")
    rig.out_value[0] = 0.6
    go(rig, 2)
    rig.reg[CHASE_PARAM].set(True)
    go(rig, 2)
    rig.reg[CHASE_PARAM].set(False)
    shown = p.value
    rig.out_value[0] = 0.5
    rig.view.rate[0] = 0.0
    assert labels(rig) == []
    go(rig, 2)
    assert p.base == pytest.approx(shown, abs=0.05)


# ---------------------------------------------------------------- the projector's hold

@pytest.fixture()
def held(rig):
    rig.renderer = SimpleNamespace(wiring=None, ghost_states={})
    rig.hold = H.Hold(rig.reg, rig.renderer, undo=rig.undo, section=rig.presets.graph)
    H.register(rig.reg, rig.hold)
    return rig


def test_under_the_projectors_hold_the_press_is_refused(held):
    p = routed(held)
    held.out_value[0] = 0.6
    go(held, 2)
    base = p.base
    assert held.hold.engage()
    held.reg[CHASE_PARAM].set(True)
    assert not held.reg[CHASE_PARAM].value and not held.reg.chasing
    go(held, 2)
    assert p.base == pytest.approx(base) and held.hold.changed() == []
    held.hold.take()
    held.reg[CHASE_PARAM].set(True)
    assert held.reg.chasing, "let go of the hold, the verb works"


def test_engaging_the_hold_lets_the_verb_go_and_keeps_its_commit(held):
    p = routed(held)
    held.out_value[0] = 0.6
    go(held, 2)
    held.reg[CHASE_PARAM].set(True)
    go(held, 2)
    shown = p.base
    assert held.hold.engage()
    assert not held.reg.chasing and held.undo._open is None and not held.undo._keep
    assert labels(held) == [CHASE_LABEL], "the step closed before the point Drop goes back to"
    held.out_value[0] = 0.5
    go(held, 3)
    assert p.base == pytest.approx(shown) and held.hold.changed() == []
    held.hold.drop()
    assert p.base == pytest.approx(shown), "Drop goes back to the hold's point, the commit in it"


# ---------------------------------------------------------------- pressing it

def _note(on: bool, number: int = 94, channel: int = 0):
    kind = "note_on" if on else "note_off"
    return mido.Message(kind, channel=channel, note=number, velocity=127 if on else 0)


def test_a_desk_button_learned_on_it_is_held_not_latched(rig):
    src = "note:0:94"
    rig.learn.arm(CHASE_PARAM)
    assert rig.learn.learn_control(src)
    row = [b for b in rig.table.bindings if b.target == CHASE_PARAM]
    assert [b.op for b in row] == ["momentary"]
    rig.inp.queue.append(_note(True))
    rig.midi.poll()
    assert rig.reg.chasing
    rig.inp.queue.append(_note(False))
    rig.midi.poll()
    assert not rig.reg.chasing


def test_a_pad_button_learned_on_it_is_held(rig):
    rig.learn.arm(CHASE_PARAM)
    assert rig.learn.learn_pad_button("pad:Y")
    row = [b for b in rig.table.bindings if b.target == CHASE_PARAM]
    assert [b.op for b in row] == ["momentary"]


def test_a_reconnect_lets_it_go(rig):
    """A lost note-off must not leave the verb on."""
    rig.reg[CHASE_PARAM].set(True)
    rig.midi._enter()
    assert not rig.reg.chasing
