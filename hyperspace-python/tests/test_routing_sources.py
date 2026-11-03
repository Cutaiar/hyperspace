"""Plan 44 D2 — `routing_sources.Sources`, the router's shared half, and
what stays each router's own: an address resolved against the router's
own table, the tables held weakly, one clock for every router, and a
router from before D2 that a hot reload re-classes."""

from __future__ import annotations

import gc

import numpy as np
import pytest

from hyperspace import tempo
from hyperspace.motion import OFF, Motion
from hyperspace.params import Registry
from hyperspace.routing import Binding, Bindings, Router, Sources


def _pair():
    """Two routers over one `Sources`, each over its own registry and table."""
    src = Sources()
    a = Router(Registry(), Bindings([]), src)
    b = Router(Registry(), Bindings([]), src)
    return src, a, b


def test_each_router_resolves_an_address_against_its_own_tables_primaries():
    """``axis@pad:RT`` means the bare `axis` lanes only where `pad` is the
    table's primary pad (plan 27 B6): two routers over one `Sources`, two
    tables with different primaries, two answers — no "first table"."""
    src, a, b = _pair()
    src.names["axis"] = {"RT": 5}
    a.table.primaries = {"axis": "pad"}
    b.table.primaries = {"axis": "p2"}
    assert a.lane("axis@pad:RT") == ("axis", 5)
    assert b.lane("axis@pad:RT") == ("axis@pad", -1)     # another pad's, unpublished
    b.table.primaries = {"axis": "pad"}                  # a new dict: resolved again
    assert b.lane("axis@pad:RT") == ("axis", 5)
    assert not hasattr(src, "table")


def test_each_router_reads_the_pad_feel_of_its_own_table():
    _, a, b = _pair()
    a.table.pad_feel = Motion("follow", atk=0.0, rel=0.4)
    assert a.source_feel("axis") == a.table.pad_feel and b.source_feel("axis") == OFF
    assert a.source_feel("hand") == OFF
    assert a.felt("axis", [1.0], 1 / 60) == [1.0]        # a's feel is on
    assert b.felt("axis", [1.0], 1 / 60) is None         # b's is off: its followers dropped


def test_the_sources_hold_the_tables_weakly():
    """A router dropped (the panel's router swap) lets its table go; the
    registry's rig facts are never written into it again."""
    src, a, b = _pair()
    assert src.tables == [a.table, b.table]
    del b
    gc.collect()
    assert src.tables == [a.table]

    class Devs:
        def continuous_schemes(self):
            return ("lane",)

        def primaries(self):
            return {"axis": "pad"}

    src.use(Devs())
    assert a.table.primaries == {"axis": "pad"}


def test_one_clock_for_every_router_over_the_sources():
    """The sources own the clock (plan 44 §2): the first bank's clock
    becomes it, the same clock again is fine, another is refused."""
    from hyperspace import lfo

    src, a, b = _pair()
    c = tempo.Clock()
    a.use_lfos(lfo.LFOs(), c)
    assert src.clock is c and a.clock is c and b.clock is c
    b.use_lfos(lfo.LFOs(), c)
    with pytest.raises(ValueError, match="one clock"):
        b.use_bank(lfo.LFOs(), tempo.Clock())
    assert src.clock is c


def test_a_router_from_before_the_split_survives_a_hot_reload():
    """A Router built before plan 44 D2 kept its feeds, labels, names and
    clock in its own __dict__ and has no sources; re-classed by a hot
    reload it gets sources of its own holding what it had been fed, and
    its pass runs on them (audit H1's survival, as the restart is asked)."""
    reg = Registry()
    v = {"x": 0.5}
    reg.continuous("t.x", "x", lambda: v["x"], lambda x: v.__setitem__("x", x), group="view")
    table = Bindings([Binding("hand:right.y", "t.x", "position", 1.0)])
    old = Router.__new__(Router)                         # the instance as it was
    clock = tempo.Clock()
    old.__dict__.update(reg=reg, table=table, devices=None, clock=clock,
                        feeds={"hand": np.array([0.9])}, labels={"hand": ["R y"]},
                        gates={}, rests={"hand": [0.5]}, _codes={},
                        _names={"hand": {"right.y": 0}}, _macro_bases={},
                        _macros_seen=table.macros_serial)
    assert "_sources" not in old.__dict__
    assert old.labels["hand"] == ["R y"] and old.clock is clock
    assert old.lane("hand:right.y") == ("hand", 0)
    old.modulate()
    reg.apply()
    assert reg["t.x"].eff_norm == pytest.approx(0.9)
    assert old.sources.tables == [table]
