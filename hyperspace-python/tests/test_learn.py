"""learn.py — the armed param and the held question, shared by every
adapter (plan 11 WP5, audit B3 and B4). A hand completes a learn with no
MIDI adapter anywhere; a `band.sel.*` alias learns onto the band it
stands for; the referee's refusal is held for the prompt."""

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
    table's referee, written to the file — no MidiIO exists here (B3). On
    an owned target it is held in `pending`; a new learn forgets it."""
    lrn, t = rig.learn, rig.table
    lrn.arm("view.inst_amp")
    assert lrn.learning == "view.inst_amp"
    lrn.learn_source("hand:3", when="hand:14")
    assert lrn.learning is None and lrn.pending is None
    b = t.owner("view.inst_amp")
    assert (b.source, b.op, b.value, b.when) == ("hand:3", "position", 1.0, "hand:14")
    assert "learned view.inst_amp" in lrn.last
    assert Bindings.load(tmp_path / "bindings.json", legacy_midi=None).owner("view.inst_amp") == b
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
