"""The base chase (plan 52): while held, the performer is committed into the
base; let go, the look stays where the performer left it.

The param model first, against a twin the verb never touches (what shows is
what would have shown), then the rig: the real router's rows, undo's one step
per hold, the dirty dot, Learn, and two decks over one session."""

from __future__ import annotations

import math
import random
from types import SimpleNamespace

import mido
import pytest
from test_undo import boot, frames, labels

from hyperspace import lfo
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.control import Control
from hyperspace.deck import Deck
from hyperspace.params import (
    CHASE_LABEL,
    CHASE_PARAM,
    Registry,
    build_patch,
    build_meta,
    chase_reaches,
)
from hyperspace.routing import Binding, Bindings, latch_refusal, press_momentary
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
    assert p.value == pytest.approx(0.8), "back lower than it left: still on its way home"
    land(p, 0.0)
    land(p, 0.1)
    assert p.value == pytest.approx(0.9), "home, it rides in full"


def test_a_knob_then_its_undo_on_a_commit_counts_nothing_twice(rig):
    p = routed(rig)
    rig.out_value[0] = 0.6
    go(rig, 2)
    rig.reg[CHASE_PARAM].set(True)
    go(rig, 2)
    rig.reg[CHASE_PARAM].set(False)
    settle_with(rig)
    shown = p.value
    p.set(p.base * 0.5)
    settle_with(rig)
    moved = p.value
    assert moved == pytest.approx(shown * 0.5)
    assert rig.undo.undo()
    go(rig, 2)
    assert p.value == pytest.approx(shown), "the commit's ledger came back with its base"
    assert rig.undo.redo()
    go(rig, 2)
    assert p.value == pytest.approx(moved)


def test_a_second_hold_undone_keeps_the_first_holds_ledger(rig):
    p = routed(rig)
    rig.out_value[0] = 0.55
    go(rig, 2)
    rig.reg[CHASE_PARAM].set(True)
    go(rig, 2)
    rig.reg[CHASE_PARAM].set(False)
    settle_with(rig)
    first = p.base
    rig.out_value[0] = 0.6
    go(rig, 2)
    riding = p.value
    assert riding > first
    rig.reg[CHASE_PARAM].set(True)
    go(rig, 2)
    rig.reg[CHASE_PARAM].set(False)
    assert p.base == pytest.approx(riding)
    assert rig.undo.undo()
    go(rig, 2)
    assert p.base == pytest.approx(first)
    assert p.value == pytest.approx(riding), "as it stood before that hold"


def test_a_load_under_a_live_route_inherits_no_commit(rig):
    """The saved base plus the route's whole offset: a look holds no commit
    it never made. Its undo brings the commit back, nothing counted twice."""
    p = routed(rig)
    rig.loaded_patch.save_as("LOOK")
    saved = p.norm
    rig.out_value[0] = 0.6
    go(rig, 2)
    offset = p.eff_norm - p.norm
    assert offset > 0
    rig.reg[CHASE_PARAM].set(True)
    go(rig, 2)
    rig.reg[CHASE_PARAM].set(False)
    settle_with(rig)
    committed, shown = p.norm, p.eff_norm
    assert committed == pytest.approx(saved + offset) and shown == pytest.approx(committed)
    rig.loaded_patch.load("LOOK")
    go(rig, 2)
    p = rig.reg[p.id]
    assert p.norm == pytest.approx(saved)
    assert p.eff_norm == pytest.approx(saved + offset), "base plus the route, in full"
    assert rig.undo.undo()
    go(rig, 2)
    assert p.norm == pytest.approx(committed) and p.eff_norm == pytest.approx(shown)


def test_a_load_with_the_same_value_as_the_commit_inherits_nothing(rig):
    p = routed(rig)
    rig.out_value[0] = 0.6
    go(rig, 2)
    rig.reg[CHASE_PARAM].set(True)
    go(rig, 2)
    rig.reg[CHASE_PARAM].set(False)
    offset = p._trim
    assert offset > 0
    rig.loaded_patch.save_as("SAME")                # the committed value, in a file
    rig.loaded_patch.load("SAME")
    go(rig, 2)
    assert p.eff_norm == pytest.approx(p.norm + offset)


def test_a_loads_pose_inherits_no_commit(rig):
    p = routed(rig, "rot.phase.XY")
    rig.out_value[0] = 0.6
    go(rig, 2)
    rig.reg[CHASE_PARAM].set(True)
    go(rig, 2)
    rig.reg[CHASE_PARAM].set(False)
    assert p._trim
    rig.loaded_patch.save_as("POSED")
    rig.loaded_patch.load("POSED")
    assert p._trim == 0.0


def test_a_row_made_after_the_last_one_went_rides_in_full(rig):
    """The ledger was about the row that went."""
    p = routed(rig)
    row = rig.table.routes_to(p.id)[-1]
    rig.out_value[0] = 0.6
    go(rig, 2)
    rig.reg[CHASE_PARAM].set(True)
    go(rig, 2)
    rig.reg[CHASE_PARAM].set(False)
    offset = p._trim
    assert offset > 0
    rig.table.remove(row)
    go(rig, 2)
    assert p._trim == 0.0 and p.value == pytest.approx(p.base)
    base = p.norm
    rig.table.add(Binding("hand:1", p.id, "push", 1.0, rest=0.5))
    go(rig, 2)
    assert p.eff_norm == pytest.approx(base + offset)


def test_a_source_flickering_under_the_verb_commits_once(reg):
    """A lane gone NaN, a shut gate, a pad off for one frame: a source that
    has not moved adds nothing however often it drops out."""
    p = declare(reg, "view.a", 0.5)
    reg.base_chase(True)
    for _ in range(6):
        land(p, 0.1)
        assert p.value == pytest.approx(0.6)
        p.apply()                              # the gap
        assert p.value == pytest.approx(0.6)
    assert p.base == pytest.approx(0.6)


def test_a_source_flickering_after_the_release_stays_put(reg):
    p = declare(reg, "view.a", 0.5)
    reg.base_chase(True)
    land(p, 0.3)
    reg.base_chase(False)
    for _ in range(6):
        p.apply()
        assert p.value == pytest.approx(0.8)
        land(p, 0.3)
        assert p.value == pytest.approx(0.8)


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


def test_a_restore_brings_the_ledger_of_the_base_it_brings(reg):
    p = declare(reg, "view.a", 0.5)
    land(p, 0.2)
    reg.base_chase(True)
    land(p, 0.2)
    reg.base_chase(False)
    assert p.base == pytest.approx(0.7)
    # an undo's state says what that base held
    reg.restore({"view.a": 0.7}, trims={"view.a": 0.2})
    land(p, 0.2)
    assert p.value == pytest.approx(0.7), "not 0.9"
    # a base that held nothing: the route rides in full
    reg.restore({"view.a": 0.5}, trims={})
    land(p, 0.2)
    assert p.value == pytest.approx(0.7) and p.base == pytest.approx(0.5)
    # the same base through a road with no state, a load's: it holds no commit
    reg.restore({"view.a": 0.7}, trims={"view.a": 0.2})
    reg.restore({"view.a": 0.7})
    land(p, 0.2)
    assert p.value == pytest.approx(0.9)


# ---------------------------------------------------------------- the reach

def test_the_verb_reaches_continuous_modulatable_look_params():
    chain = Analyzer(Analyser())
    meta_reg = build_meta(Control(chain), SimpleNamespace(chain=chain))
    reg = build_patch(ViewState(), meta_reg=meta_reg)
    reached = {p.id for p in reg if chase_reaches(p)}
    assert "view.bright" in reached and "rot.rate.XY" in reached and "camera.yaw" in reached
    for p in reg:
        if p.id in reached:
            assert p.modulatable and p.kind.value == "continuous"
    assert "master.gain" not in reached, "a session param is the room's"
    assert not any(p.id in reached for p in meta_reg)
    reg["macro.1"]                             # declared
    assert not any(i.startswith("macro.") for i in reached), "a macro's base moves its subscribers"
    assert CHASE_PARAM not in reached and not reg[CHASE_PARAM].persist
    assert CHASE_PARAM not in meta_reg, "every deck has its own"


def test_two_decks_chase_alone_and_leave_the_meta_alone():
    chain = Analyzer(Analyser())
    meta_reg = build_meta(Control(chain), SimpleNamespace(chain=chain))
    a = build_patch(ViewState(), meta_reg=meta_reg)
    b = build_patch(ViewState(), meta_reg=meta_reg)
    a[CHASE_PARAM].set(True)
    assert a.chasing and not b.chasing and not b[CHASE_PARAM].value
    pa, pb = a["view.bright"], b["view.bright"]
    was_a, was_b = pa.base, pb.base
    m = meta_reg["master.gain"]
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


def test_a_lane_gone_nan_does_not_commit_again_through_the_router(rig):
    p = routed(rig)
    rig.out_value[0] = 0.6
    rig.reg[CHASE_PARAM].set(True)
    go(rig, 2)
    shown = p.value
    for _ in range(4):
        rig.out_value[0] = float("nan")        # out of view for a frame
        go(rig)
        rig.out_value[0] = 0.6
        go(rig)
        assert p.value == pytest.approx(shown)
    rig.reg[CHASE_PARAM].set(False)
    assert p.base == pytest.approx(shown)


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


def test_undo_and_redo_with_a_live_push_show_what_stood_each_side(rig):
    """A steady push after undoing the hold: the old base plus the push, as
    if the verb had never been held; redo, the commit, not counted twice."""
    p = routed(rig)
    start = p.base
    rig.out_value[0] = 0.6
    go(rig, 2)
    shown = p.value
    assert shown != pytest.approx(start)
    rig.reg[CHASE_PARAM].set(True)
    go(rig, 2)
    rig.reg[CHASE_PARAM].set(False)
    assert rig.undo.undo()
    go(rig, 2)
    assert p.base == pytest.approx(start) and p.value == pytest.approx(shown)
    assert rig.undo.redo()
    go(rig, 2)
    assert p.base == pytest.approx(shown) and p.value == pytest.approx(shown), "not counted twice"


def test_an_undo_under_the_verb_ends_it(rig):
    """One hold is never more than one step: the undo takes the hold back and
    the verb lets go, so the source moving on opens nothing."""
    p = routed(rig)
    start = p.base
    rig.reg[CHASE_PARAM].set(True)
    rig.out_value[0] = 0.6
    go(rig, 2)
    assert rig.undo.undo()
    assert not rig.reg.chasing and not rig.reg[CHASE_PARAM].value
    assert p.base == pytest.approx(start)
    assert rig.undo.redos, "the redo stands"
    rig.out_value[0] = 0.7
    settle_with(rig)
    assert p.base == pytest.approx(start) and rig.undo.redos and labels(rig) == []
    rig.reg[CHASE_PARAM].set(False)            # the hand comes off: nothing to do
    assert not rig.reg.chasing and labels(rig) == []


def test_an_action_under_the_verb_ends_it_and_is_its_own_step(rig):
    p = routed(rig)
    rig.reg[CHASE_PARAM].set(True)
    rig.undo.push("an action")                 # the very frame of the press
    assert not rig.reg.chasing
    assert labels(rig) == ["an action"], "a press that moved nothing leaves no step"
    rig.undo.clear()
    rig.reg[CHASE_PARAM].set(True)
    rig.out_value[0] = 0.6
    go(rig, 2)
    moved = p.base
    rig.undo.push("a later action")
    assert not rig.reg.chasing and labels(rig) == [CHASE_LABEL, "a later action"]
    rig.out_value[0] = 0.7
    go(rig, 2)
    assert p.base == pytest.approx(moved)


def test_an_action_open_at_the_press_is_not_pinned(rig):
    routed(rig)
    rig.undo.push("an action")
    rig.reg["view.bright"].set(0.123)
    rig.reg[CHASE_PARAM].set(True)
    settle_with(rig)
    rig.reg[CHASE_PARAM].set(False)
    assert labels(rig) == ["an action"]
    assert rig.undo._open is None


def test_the_step_closes_on_the_undo_the_press_opened_it_on(rig):
    """A deck's own `Undo`: any let-go, from any road, closes that one."""
    from hyperspace.undo import Undo, installed
    own = Undo(rig.reg, rig.table)
    routed(rig)
    rig.reg.base_chase(True, steps=own)
    assert own._kept is not None and installed()._kept is None
    rig.reg[CHASE_PARAM].set(False)            # the setter names no undo
    assert own._kept is None and not rig.reg.chasing


def test_a_hold_that_moved_nothing_costs_no_step_and_no_dirty_dot(rig):
    routed(rig)
    dirty = rig.loaded_patch.is_dirty()
    rig.undo.clear()
    rig.reg[CHASE_PARAM].set(True)
    go(rig, 5)                                 # the hand at rest: nothing to commit
    rig.reg[CHASE_PARAM].set(False)
    assert labels(rig) == []
    assert rig.loaded_patch.is_dirty() == dirty


def test_a_commit_lights_the_dirty_dot_and_a_save_holds_it(rig):
    p = routed(rig)
    rig.loaded_patch.save_as("CHASED")
    assert not rig.loaded_patch.is_dirty()
    rig.out_value[0] = 0.6
    go(rig, 2)
    assert not rig.loaded_patch.is_dirty(), "an offset alone is no edit"
    rig.reg[CHASE_PARAM].set(True)
    go(rig, 2)
    rig.reg[CHASE_PARAM].set(False)
    assert rig.loaded_patch.is_dirty()
    assert rig.reg.snapshot(part="patch")[p.id] == pytest.approx(p.value)


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


# ---------------------------------------------------------------- two decks

def beside(r):
    """A second deck over `r`'s session, sources and clock, with the same
    route `routed` gives the first."""
    b = Deck.beside(r.deck, lfos=lfo.LFOs(seed=1))
    b.table.add(Binding("hand:0", "view.bright", "push", 1.0, rest=0.5))
    return b


def go_both(r, b, n=2):
    for _ in range(n):
        go(r)
        b.undo.tick(r.t)
        b.router.modulate(None)
        b.reg.apply()


def test_a_chase_on_deck_2_keeps_its_step_there_and_writes_nothing_on_deck_1(rig):
    p1 = routed(rig)
    b = beside(rig)
    p2 = b.reg["view.bright"]
    go_both(rig, b)
    b.undo.clear()
    rig.undo.clear()
    start1, start2 = p1.base, p2.base
    rig.out_value[0] = 0.6
    go_both(rig, b)
    assert b.chase(True) and b.reg.chasing and not rig.reg.chasing
    go_both(rig, b, int(SETTLE_S * 60) + 5)    # past the settle time, still one step
    assert p2.base != pytest.approx(start2), "deck 2's look took it"
    assert p2.base == pytest.approx(p2.value)
    assert p1.base == pytest.approx(start1) and not p1._trim, "deck 1's did not"
    assert p1.value != pytest.approx(start1), "and its route rides on as ever"
    assert not b.chase(False)
    assert [s.label for s in b.undo.stack] == [CHASE_LABEL]
    assert labels(rig) == [] and rig.undo._kept is None
    assert b.undo.undo()
    assert p2.base == pytest.approx(start2)


def test_deck_2s_control_uses_deck_2s_undo(rig):
    routed(rig)
    b = beside(rig)
    go_both(rig, b)
    b.undo.clear()
    rig.undo.clear()
    b.reg[CHASE_PARAM].set(True)
    assert b.undo._kept is not None and rig.undo._kept is None
    rig.out_value[0] = 0.6
    go_both(rig, b)
    b.reg[CHASE_PARAM].set(False)
    assert b.undo._kept is None
    assert [s.label for s in b.undo.stack] == [CHASE_LABEL] and labels(rig) == []


# ---------------------------------------------------------------- pressing it

def _note(on: bool, number: int = 94, channel: int = 0):
    kind = "note_on" if on else "note_off"
    return mido.Message(kind, channel=channel, note=number, velocity=127 if on else 0)


def _row_on_desk(rig, src: str = "note:0:94") -> Binding:
    """A person's row on a desk button, as `bindings.json` may hold one: since row 746 no
    Learn lands one (row 755), and a file's preset-layer row on it drops with a note."""
    return rig.table.add(Binding(src, CHASE_PARAM, "momentary"))


def test_a_desk_button_cannot_be_learned_on_it(rig):
    """Row 755: refused, per the seventh round, in words that say where its road is."""
    rig.learn.arm(CHASE_PARAM)
    assert not rig.learn.learn_control("note:0:94")
    assert "Learn pad" in rig.learn.last
    assert [b.source for b in rig.table.bindings if b.target == CHASE_PARAM] == ["pad:VIEW"]


def test_a_desk_row_on_it_is_held_not_latched(rig):
    src = "note:0:94"
    _row_on_desk(rig, src)
    row = [b for b in rig.table.bindings if b.source == src and b.target == CHASE_PARAM]
    assert [(b.target, b.op) for b in row] == [(CHASE_PARAM, "momentary")]
    rig.inp.queue.append(_note(True))
    rig.midi.poll()
    assert rig.reg.chasing
    rig.inp.queue.append(_note(False))
    rig.midi.poll()
    assert not rig.reg.chasing


def test_a_knob_is_refused_in_words(rig):
    rig.learn.arm(CHASE_PARAM)
    assert not rig.learn.learn_control("cc:0:48")
    assert rig.learn.refused
    assert [b.source for b in rig.table.bindings if b.target == CHASE_PARAM] == ["pad:VIEW"]


class Pad:
    """One button on a pad, read as `Router.pad` reads it."""

    def __init__(self):
        self.on, self.is_down, self.was_down, self.hat = True, False, False, 0

    def lanes(self):
        return None

    def down(self, _code):
        return self.is_down

    def pressed(self, _code):
        return self.is_down and not self.was_down

    def released(self, _code):
        return self.was_down and not self.is_down

    def hat_pressed(self, _code):
        return False

    def hat_released(self, _code):
        return False


def test_a_pad_button_learned_on_it_is_held_and_a_lost_pad_lets_go(rig):
    for b in [b for b in rig.table.bindings if b.target == CHASE_PARAM]:
        rig.table.remove(b)                    # BACK's factory row: this stub is one button
    rig.learn.arm(CHASE_PARAM)
    assert rig.learn.learn_pad_button("pad:Y")
    row = [b for b in rig.table.bindings if b.target == CHASE_PARAM]
    assert [b.op for b in row] == ["momentary"]
    pad = Pad()
    pad.is_down = True
    rig.router.pad(pad, now=0.0)
    assert rig.reg.chasing
    pad.was_down = True
    rig.router.pad(pad, now=0.1)
    assert rig.reg.chasing, "still held"
    pad.on = False                             # asleep, or unplugged, with the button down
    rig.router.pad(pad, now=0.2)
    assert not rig.reg.chasing
    # …and the totem taking the button has the same hole
    pad.on, pad.was_down = True, False
    rig.router.pad(pad, now=0.3)
    assert rig.reg.chasing
    pad.was_down = True
    rig.router.pad(pad, now=0.4, skip=frozenset({"pad:Y"}))
    assert not rig.reg.chasing
    # a release as ever
    pad.was_down = False
    rig.router.pad(pad, now=0.5)
    assert rig.reg.chasing
    pad.was_down, pad.is_down = True, False
    rig.router.pad(pad, now=0.6)
    assert not rig.reg.chasing


def test_a_desk_button_and_a_pad_button_hold_it_together(rig):
    """Brushing the pad's button does not end what the APC's holds, or the
    other way about; a desk cable lost lets go only of the desk's."""
    _row_on_desk(rig)
    pad = Pad()
    rig.inp.queue.append(_note(True))
    rig.midi.poll()
    assert rig.reg.chasing
    pad.is_down = True
    rig.router.pad(pad, now=0.0)                # BACK down
    pad.was_down, pad.is_down = True, False
    rig.router.pad(pad, now=0.1)                # …and up: a brush
    assert rig.reg.chasing, "the APC's button still holds it"
    pad.was_down, pad.is_down = False, True
    rig.router.pad(pad, now=0.2)
    rig.inp.queue.append(_note(False))
    rig.midi.poll()
    assert rig.reg.chasing, "the pad's button still holds it"
    rig.inp.queue.append(_note(True))
    rig.midi.poll()
    rig.midi._let_go_held()                     # the cable went
    assert rig.reg.chasing, "the pad's button still holds it"
    pad.was_down, pad.is_down = True, False
    rig.router.pad(pad, now=0.3)
    assert not rig.reg.chasing


def test_a_desk_closed_lets_go(rig):
    """A desk's device closed with its button down: no poll follows."""
    _row_on_desk(rig)
    rig.inp.queue.append(_note(True))
    rig.midi.poll()
    assert rig.reg.chasing
    rig.midi.close()
    assert not rig.reg.chasing and not rig.reg[CHASE_PARAM].__dict__["_pressed_by"]


def test_a_cc_row_on_it_records_no_press_and_a_lost_desk_lets_go(rig):
    """A `momentary` row on a knob (by hand: Learn refuses one) lands as `abs`, so
    the ledger never hears of it, and losing the desk ends it all the same."""
    rig.table.add(Binding("cc:0:48", CHASE_PARAM, "momentary"))
    rig.inp.queue.append(mido.Message("control_change", channel=0, control=48, value=127))
    rig.midi.poll()
    assert not rig.reg[CHASE_PARAM].__dict__.get("_pressed_by")
    rig.reg[CHASE_PARAM].set(True)
    rig.midi._let_go_held()
    assert not rig.reg.chasing


@pytest.mark.parametrize("lost", ["close", "_let_go_held"])
def test_a_desk_lost_leaves_what_another_desk_holds(rig, lost):
    """A press recorded by one desk is that desk's: losing the other leaves it,
    qualified or not, and its own release still ends the chase."""
    p = rig.reg[CHASE_PARAM]
    press_momentary(p, "note@launch:0:94", True)     # the second desk's button
    _row_on_desk(rig)
    rig.inp.queue.append(_note(True))
    rig.midi.poll()
    getattr(rig.midi, lost)()
    assert rig.reg.chasing, "the second desk's button still holds it"
    assert p.__dict__["_pressed_by"] == {"note@launch:0:94"}
    press_momentary(p, "note@launch:0:94", False)
    assert not rig.reg.chasing


@pytest.mark.parametrize("change", ["removed", "retargeted", "switched off", "its rows forgotten"])
def test_a_desk_row_changed_under_its_button_still_releases(rig, change):
    _row_on_desk(rig)
    rig.inp.queue.append(_note(True))
    rig.midi.poll()
    assert rig.reg.chasing
    row = next(b for b in rig.table.bindings if b.source == "note:0:94" and b.target == CHASE_PARAM)
    if change == "removed":
        rig.table.remove(row)
    elif change == "retargeted":
        row.target = "view.lines"               # as the desk rows' combo does
    elif change == "switched off":
        row.enabled = False
    else:
        rig.midi._held.clear()                  # the release finds no rows of the press
        rig.table.remove(row)
    rig.inp.queue.append(_note(False))
    rig.midi.poll()
    assert not rig.reg.chasing and not rig.reg[CHASE_PARAM].__dict__["_pressed_by"]


def test_a_lost_pad_leaves_a_toggle_it_did_not_hold(rig):
    rig.reg[CHASE_PARAM].set(True)             # held from elsewhere
    pad = Pad()
    pad.on = False
    rig.router.pad(pad, now=0.0)
    assert rig.reg.chasing


@pytest.mark.parametrize("row", [Binding("key:S", CHASE_PARAM, "toggle"),
                                 Binding("note:0:94", CHASE_PARAM, "toggle"),
                                 Binding("note:0:94", CHASE_PARAM, "set", 1.0)],
                         ids=["key", "note-toggle", "set"])
def test_a_row_that_could_latch_it_is_refused(row):
    assert latch_refusal(row) is not None
    with pytest.raises(ValueError):
        Bindings().bind(row, write=False)
    kept = Bindings.from_json({"bindings": [row.to_json()]}, desk=False)
    assert not [b for b in kept.bindings if b.target == CHASE_PARAM]


def test_a_cable_pulled_mid_hold_lets_it_go(rig):
    """A note-off that is never coming: at once, not at the reconnect, and
    once: a desk that stays away does not hold the verb off for others."""
    rig.reg[CHASE_PARAM].set(True)
    rig.midi.poll()
    assert rig.reg.chasing
    rig.midi.ports.inp = rig.midi.ports.out = None
    rig.midi.ports.retry = lambda: False       # (no looking for a real desk)
    assert not rig.midi.on
    rig.midi.poll()
    assert not rig.reg.chasing
    rig.reg[CHASE_PARAM].set(True)
    rig.midi.poll()
    assert rig.reg.chasing


def test_a_reconnect_lets_it_go(rig):
    """A lost note-off must not leave the verb on."""
    rig.reg[CHASE_PARAM].set(True)
    rig.midi._enter()
    assert not rig.reg.chasing
