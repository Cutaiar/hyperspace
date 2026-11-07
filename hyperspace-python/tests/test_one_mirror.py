"""LY1: one mirror. An extra hands node's `GhostState` follows `ghost.mirror`,
so a hands node adds nothing to what's shared; and a `Deck`'s graph dropping a
node removes nothing from the other `Deck` ("no loadable patch can affect
another", the owner). The leak tests run both ways on two real `Deck`s.
"""

from __future__ import annotations

import json

import pytest
from test_loadable import put
from test_undo import boot

from hyperspace.deck import Deck
from hyperspace.library import PROJECT_SUFFIX, PROJECTS
from hyperspace.params import is_shared_meta_id
from hyperspace.routing import is_meta_row

TWO_HANDS = {"nodes": [{"kind": "hands", "into": "scene"}, {"kind": "hands", "instance": 2}]}
ONE_HAND = {"nodes": [{"kind": "hands", "into": "scene"}]}


class Two:
    """Two real decks over one meta controller, deck 1 from the rig."""

    def __init__(self, home):
        self.rig = boot(home)
        self.home = home
        self.decks = {"a": self.rig.deck, "b": Deck.beside(self.rig.deck)}
        self.a, self.b = self.decks["a"], self.decks["b"]
        self.meta = self.a.meta_reg

    def land(self, deck, name: str, graph: dict) -> None:
        deck.loaded_patch.load_doc(json.loads(put(self.home, name, graph=graph).read_text()), None)


@pytest.fixture()
def two(tmp_path):
    return Two(tmp_path / "home")


def _ids(reg) -> list[str]:
    return list(reg._p)


BOTH_WAYS = [("a", "b"), ("b", "a")]


@pytest.mark.parametrize("dropper,holder", BOTH_WAYS)
def test_a_deck_dropping_its_hands_node_takes_nothing_from_the_other(two, dropper, holder):
    drops, holds = two.decks[dropper], two.decks[holder]
    two.land(two.a, "Glass", TWO_HANDS)
    two.land(two.b, "Glass", TWO_HANDS)
    held, shared, serial = _ids(holds.reg), _ids(two.meta), holds.reg.serial
    state = holds.graph.states["ghost.2"]
    assert "ghost.2.alpha" in holds.reg

    two.land(drops, "Plain", ONE_HAND)

    assert "ghost.2.alpha" not in drops.reg           # (it did drop it)
    assert _ids(holds.reg) == held and holds.reg.serial == serial
    assert _ids(two.meta) == shared
    # the one mirror still reaches the node the other deck holds
    two.a.reg["ghost.mirror"].set(True)
    assert state.mirror is True and holds.graph.states["ghost.2"] is state
    two.b.reg["ghost.mirror"].set(False)
    assert state.mirror is False


@pytest.mark.parametrize("dropper,holder", BOTH_WAYS)
def test_a_deck_taking_or_dropping_a_hands_node_adds_nothing_to_what_is_shared(two, dropper, holder):
    drops, holds = two.decks[dropper], two.decks[holder]
    shared, other = _ids(two.meta), _ids(holds.reg)

    two.land(drops, "Glass", TWO_HANDS)
    assert "ghost.2.alpha" in drops.reg and "ghost.2.mirror" not in drops.reg
    assert _ids(two.meta) == shared and _ids(holds.reg) == other

    two.land(drops, "Plain", ONE_HAND)
    assert _ids(two.meta) == shared and _ids(holds.reg) == other


def test_a_node_taken_with_the_mirror_on_starts_flipped_on_either_deck(two):
    two.a.reg["ghost.mirror"].set(True)
    two.land(two.a, "Glass", TWO_HANDS)
    two.land(two.b, "Glass", TWO_HANDS)
    assert two.a.graph.states["ghost.2"].mirror and two.b.graph.states["ghost.2"].mirror
    assert two.a.graph.states["ghost.2"] is not two.b.graph.states["ghost.2"]


@pytest.mark.parametrize("dropper,holder", BOTH_WAYS)
def test_no_section_a_deck_drops_reaches_the_shared_table(two, dropper, holder):
    """The shape, not the one id: per-deck sections filled and emptied on one
    deck, then every patch prefix swept from its registry, leave the other deck
    and the meta controller as they were, the same param objects."""
    drops, holds = two.decks[dropper], two.decks[holder]
    shared = {p.id: p for p in two.meta}
    other = {p.id: p for p in holds.reg}
    rows = [b for b in holds.table.bindings if is_meta_row(b)]

    many = {"nodes": [{"kind": "hands", "into": "scene"}, {"kind": "hands", "instance": 2},
                      {"kind": "hands", "instance": 3}]}
    two.land(drops, "Many", many)
    drops.lfos.add()
    drops.envs.add()
    two.land(drops, "Plain", ONE_HAND)
    for bank in (drops.lfos, drops.envs):
        bank.remove(bank.ids()[-1])
    for prefix in ("fx.", "ghost.", "lfo.", "env.", "seq.", "switch", "mod."):
        drops.reg.remove_prefix(prefix)

    assert {p.id: p for p in two.meta} == shared
    assert {p.id: p for p in holds.reg} == other
    assert all(x is y for x, y in zip(rows, [b for b in holds.table.bindings if is_meta_row(b)],
                                      strict=True))


def test_a_decks_registry_cannot_drop_a_shared_param(two):
    """The one door: `Registry.remove` on a deck keeps a shared param, whatever
    the caller; the meta controller's own remove takes it from every deck."""
    pid = next(p.id for p in two.meta if is_shared_meta_id(p.id))
    param = two.meta[pid]
    assert two.a.reg.remove(pid) is None and two.b.reg.remove_prefix(pid) == []
    assert two.a.reg[pid] is param and two.b.reg[pid] is param and two.meta[pid] is param
    assert two.meta.remove(pid) is param
    assert pid not in two.a.reg and pid not in two.b.reg and pid not in two.meta


def test_a_show_that_holds_the_old_id_still_opens_clean_and_keeps_it(tmp_path):
    """No format move: a show file with `ghost.2.mirror` opens with no unknown id
    said, clean; a save carries the id; nothing reads it (`test_graph_json`, the
    same with a look and without the node)."""
    home = tmp_path / "home"
    rig = boot(home)
    put(home, "Glass", graph=TWO_HANDS)
    show = home / PROJECTS / f"old{PROJECT_SUFFIX}"
    show.parent.mkdir(parents=True, exist_ok=True)
    show.write_text(json.dumps({"schema": "hyperspace.project/3", "name": "old", "startup": "Glass",
                                "bank": ["Glass"], "modules": {},
                                "session": {"ghost.mirror": False, "ghost.2.mirror": True}}))
    rig.lib.warning = ""
    assert rig.lib.project.load("old") == []
    assert "unknown" not in rig.lib.warning and not rig.lib.project.is_dirty()
    state = rig.deck.graph.states["ghost.2"]
    assert "ghost.2.mirror" not in rig.reg and state.mirror is False
    rig.reg["ghost.mirror"].set(True)
    assert state.mirror is True
    rig.reg["ghost.mirror"].set(False)
    rig.lib.project.save()
    assert json.loads(show.read_text())["session"]["ghost.2.mirror"] is True
