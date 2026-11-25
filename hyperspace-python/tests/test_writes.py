"""Undo on write (hyperspace/writes.py): a write marks, an offset does not, and
`Undo.tick` takes a fingerprint only when something was marked."""

from dataclasses import dataclass, field

import pytest

from hyperspace import undo, writes
from hyperspace.params import Registry
from hyperspace.routing import Binding, Bindings


@dataclass
class Box(writes.Observed):
    a: float = 0.0
    b: float = 0.0
    run: float = 0.0
    items: list = field(default_factory=lambda: [0.0])

    @property
    def twice(self):
        return self.run * 2

    @twice.setter
    def twice(self, v):
        self.run = v / 2


@pytest.fixture
def rig():
    box, reg = Box(), Registry()
    reg.continuous("x.a", "A", *writes.cell(box, "a"), group="view")
    reg.continuous("x.b", "B", *writes.cell(box, "b"), group="view")
    reg.continuous("x.item", "I", lambda: box.items[0],
                   lambda v: box.items.__setitem__(0, v), group="view")
    table = Bindings([])
    table.bindings = [Binding("lane:0", "x.a", "push", 0.5)]
    u = undo.Undo(reg, table)
    u.box, u.looks = box, []
    take = u._fingerprint

    def counted():
        u.looks.append(1)
        return take()

    u._fingerprint = counted
    return u


def looked(u, now=1.0) -> bool:
    """Did this tick take a fingerprint? (Off the oracle, which takes one always.)"""
    was, undo.oracle = undo.oracle, None
    u.looks.clear()
    try:
        u.tick(now)
    finally:
        undo.oracle = was
    return bool(u.looks)


def test_an_idle_frame_takes_no_fingerprint(rig):
    assert not looked(rig) and not looked(rig)


@pytest.mark.parametrize("write", [
    lambda u: u.reg["x.a"].set(0.5),
    lambda u: u.reg["x.a"].nudge(0.25),
    lambda u: u.reg["x.a"].follow(0.25),
    lambda u: setattr(u.box, "a", 0.5),                     # round Param
    lambda u: u.box.items.__setitem__(0, 0.5),              # polled
    lambda u: setattr(u.table.bindings[0], "value", 0.75),  # a row in place
    lambda u: u.table.bindings.append(Binding("lane:1", "x.b", "push")),
    lambda u: u.table.bindings.clear(),
    lambda u: u.reg.toggle("x.new", "N", lambda: False, lambda v: None, group="view"),
])
def test_every_road_of_a_write_is_looked_at_the_frame_it_lands(rig, write):
    write(rig)
    assert looked(rig)
    assert not looked(rig)


def test_an_edit_round_param_is_a_step(rig):
    rig.box.a = 0.5
    rig.tick(1.0)
    rig.tick(2.0)
    assert [s.label for s in rig.stack] == ["A 0.00 → 0.50"]


def test_a_performer_marks_only_as_it_takes_and_lets_go(rig):
    p = rig.reg["x.a"]
    p.modulate(0.1)
    p.apply()
    assert looked(rig)
    for k in range(5):                       # the offset moves the object every frame
        p.modulate(0.1 * k)
        p.apply()
        assert not looked(rig)
    p.apply()
    assert looked(rig)
    rig.tick(9.0)
    assert not rig.stack


def test_a_write_under_a_performer_marks_when_the_base_takes_it(rig):
    p = rig.reg["x.a"]
    p.modulate(0.1)
    p.apply()
    rig.tick(1.0)
    rig.box.a = 0.9
    rig.tick(1.1)
    p.modulate(0.1)
    p.apply()
    assert looked(rig, 1.2)
    assert rig.stack and rig._open is not None


def test_a_cell_two_params_write_is_polled(rig):
    rig.reg.continuous("x.too", "Too", *writes.cell(rig.box, "b"), group="other", persist=False)
    looked(rig)
    assert [p.id for _, p in rig._polled] == ["x.b", "x.item"]
    other = rig.reg["x.too"]
    other.modulate(0.4)                      # an offset there is x.b's base
    other.apply()
    looked(rig)                              # (it took the param: a mark)
    other.modulate(0.7)
    other.apply()
    assert looked(rig)


def test_a_property_and_a_plain_object_are_no_cell():
    class Plain:
        a = 0.0

    assert not hasattr(writes.getter(Box(), "twice"), "cell")
    assert not hasattr(writes.getter(Plain(), "a"), "cell")
    get, put = writes.cell(Plain(), "a", int)
    put(2.7)
    assert get() == 2


def test_the_same_value_again_and_an_unread_attribute_mark_nothing(rig):
    at = writes.serial()
    rig.box.a = rig.box.a
    rig.box.run = 5.0
    Box()
    assert writes.serial() == at


@pytest.mark.parametrize("change", [
    lambda d: d.__setitem__("k", 2), lambda d: d.update(k=2), lambda d: d.pop("k"),
    lambda d: d.clear(), lambda d: d.setdefault("z", 1), lambda d: d.__delitem__("k"),
    lambda d: d.popitem(), lambda d: d.__ior__({"k": 3})])
def test_an_observed_dict_marks_every_change(change):
    d = writes.ObservedDict(k=1)
    at = writes.serial()
    change(d)
    assert writes.serial() > at


def test_a_dicts_put_is_no_mark():
    d = writes.ObservedDict(k=1)
    _get, put = writes.key(d, "k")
    at = writes.serial()
    put(5)
    assert d["k"] == 5 and writes.serial() == at


def test_a_registry_that_counts_no_writes_is_read_every_frame(rig):
    rig.reg.writes = None
    assert looked(rig) and looked(rig)


def test_rows_that_do_not_mark_are_read_every_frame(rig):
    class Row:
        pass

    row = Row()
    for k in undo.ROW_FIELDS:
        setattr(row, k, None)
    rig.table.bindings.append(row)
    assert looked(rig) and looked(rig)


def test_a_fingerprint_thrown_away_takes_no_mark_with_it(rig):
    rig.reg["x.a"].set(0.5)
    rig._fingerprint()
    assert looked(rig)


def test_the_oracle_hears_an_unmarked_write(rig, undo_oracle):
    vars(rig.box)["a"] = 0.5                 # past the hook: what no code may do
    rig.tick(1.0)
    assert undo_oracle and undo_oracle[0].startswith("x.a: 0.0 → 0.5")
    undo_oracle.clear()


def test_a_reload_keeps_the_count_and_the_cells():
    import importlib
    at = writes.serial()
    names = writes._names[(Box.__module__, Box.__qualname__)]
    old = {k: writes.__dict__[k] for k in ("Observed", "ObservedDict")}
    try:
        importlib.reload(writes)
        assert writes.serial() == at
        assert writes._names[(Box.__module__, Box.__qualname__)] is names
    finally:
        writes.__dict__.update(old)          # the classes every module here was built on


def test_a_param_declared_again_under_its_id_is_looked_at(rig):
    """A shader reload builds a new value and declares its param again over it:
    nothing is written, and the last effect's ids keep their order. A look that
    trusted the ids kept the old base, and the next edit's undo put it back
    (Devin's review of #506)."""
    new = Box(b=3.0)
    rig.tick(0.0)
    assert not looked(rig, 1.0)
    rig.reg.remove("x.item")
    rig.reg.remove("x.b")
    rig.reg.continuous("x.b", "B", *writes.cell(new, "b"), group="view")
    rig.reg.continuous("x.item", "I", lambda: rig.box.items[0],
                       lambda v: rig.box.items.__setitem__(0, v), group="view")
    assert tuple(q.id for q in rig.reg) == rig._fp[0]       # the same ids, in the same order
    rig._params()                       # (an undo or a restore asks between the ticks)
    assert looked(rig, 2.0)
    assert rig._fp[1][rig._fp[0].index("x.b")] == 3.0
    assert not looked(rig, 3.0)                             # once: the fast path is back
