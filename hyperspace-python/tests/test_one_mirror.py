"""LY1: one mirror. An extra hands node's `GhostState` follows `ghost.mirror`,
so a hands node adds nothing to what's shared; and a `Deck`'s graph dropping a
node removes nothing from the other `Deck` ("no loadable patch can affect
another", the owner). The leak tests run both ways on two real `Deck`s.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from test_loadable import put
from test_undo import boot

from hyperspace import graph as G
from hyperspace.deck import Deck
from hyperspace.ghost import GhostState
from hyperspace.ghost import register as declare_ghost
from hyperspace.graphmigrate import wired_wiring
from hyperspace.library import PROJECT_SUFFIX, PROJECTS, mirrors_apart
from hyperspace.outputs import Switches as S
from hyperspace.params import Registry, is_shared_meta_id
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
    def sweep():
        for prefix in ("fx.", "ghost.", "lfo.", "env.", "seq.", "switch", "mod."):
            drops.reg.remove_prefix(prefix)
    with pytest.warns(UserWarning, match="is shared"):
        sweep()

    assert {p.id: p for p in two.meta} == shared
    assert {p.id: p for p in holds.reg} == other
    assert all(x is y for x, y in zip(rows, [b for b in holds.table.bindings if is_meta_row(b)],
                                      strict=True))


def test_a_decks_registry_cannot_drop_a_shared_param(two):
    """The one door: `Registry.remove` on a deck keeps a shared param, whatever
    the caller; the meta controller's own remove takes it from every deck."""
    pid = next(p.id for p in two.meta if is_shared_meta_id(p.id))
    param = two.meta[pid]
    with pytest.warns(UserWarning, match=f"{pid} is shared"):
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
    assert "ghost.2.mirror differs from the Mirror" in rig.lib.warning
    state = rig.deck.graph.states["ghost.2"]
    assert "ghost.2.mirror" not in rig.reg and state.mirror is False
    rig.reg["ghost.mirror"].set(True)
    assert state.mirror is True
    rig.reg["ghost.mirror"].set(False)
    rig.lib.project.save()
    assert json.loads(show.read_text())["session"]["ghost.2.mirror"] is True


def test_only_a_mirror_that_differs_is_said():
    assert mirrors_apart({"ghost.mirror": True, "ghost.2.mirror": True}) == []
    assert mirrors_apart({"ghost.mirror": False, "ghost.2.mirror": False}) == []
    assert mirrors_apart({"ghost.2.mirror": False, "ghost.2.alpha": 0.2}) == []
    assert mirrors_apart({"ghost.mirror": True, "ghost.2.mirror": False,
                          "ghost.3.mirror": True, "ghost.alpha": 1.0}) == ["ghost.2.mirror"]


def test_a_patch_file_naming_the_old_id_is_ignored_with_a_note_not_unknown(two):
    """§9's "keep tolerating": a loadable patch holding `ghost.2.mirror`, with
    or without the node, as it was before LY1."""
    for graph in (TWO_HANDS, ONE_HAND):
        doc = json.loads(put(two.home, "Old", graph=graph,
                             values={"ghost.2.mirror": True}).read_text())
        two.rig.lib.warning = ""
        two.a.loaded_patch.load_doc(doc, None)
        notes = two.a.loaded_patch.notes
        assert "ghost.2.mirror is the session's, ignored" in notes
        assert not [n for n in notes if "unknown" in n] and "unknown" not in two.rig.lib.warning
        assert "ghost.2.mirror" not in two.a.reg


def test_an_extra_node_on_a_bare_registry_declares_the_one_mirror_and_follows_it():
    reg = Registry()
    extra, main = GhostState(), GhostState()
    declare_ghost(reg, extra, 2)
    assert "ghost.mirror" in reg and "ghost.2.mirror" not in reg
    declare_ghost(reg, main)
    reg["ghost.mirror"].set(True)
    assert extra.mirror is True and main.mirror is True


RELOAD_SCRIPT = """
from hyperspace import ghost as G
from hyperspace.hotreload import HotReloader
from hyperspace.params import Registry

reg = Registry()
main, held, new = G.GhostState(), G.GhostState(), G.GhostState()
G.register(reg, main)
G.register(reg, held, 2)
# what a running app from before LY1 holds: the node on its own stale param
stale = G.RoomSetting(False)
stale.follow(held)
reg.toggle("ghost.2.mirror", "Ghost 2 mirror", lambda: stale.value, stale.set, group="ghost",
           modulatable=False).__dict__["room"] = stale
old_room = reg["ghost.mirror"].room
old_room._states = [ref for ref in old_room._states if ref() is not held]

r = HotReloader(lambda: [], modules=("ghost",), period=0.0)
r._mtimes["ghost"] = 0.0                     # as if ghost.py had just been saved
assert r.poll(now=1.0), r.error
assert not isinstance(old_room, G.RoomSetting), "the reload should leave the old class behind"

G.register(reg, new, 3)                      # the first new extra node after the reload
assert reg["ghost.mirror"].room is old_room and isinstance(old_room, G.RoomSetting)
G.register(reg, held, 2)                     # a held node landed again: the early return
reg["ghost.mirror"].set(True)
assert main.mirror is True, "the main hands stopped following"
assert new.mirror is True, "the new node does not follow"
assert held.mirror is True, "the held node does not follow"
reg["ghost.mirror"].set(False)
assert (main.mirror, new.mirror, held.mirror) == (False, False, False)
print("ok")
"""


def test_a_real_hot_reload_keeps_every_node_on_the_one_mirror():
    out = subprocess.run([sys.executable, "-c", RELOAD_SCRIPT], capture_output=True, text=True,
                         check=False, cwd=str(Path(__file__).parents[1]), timeout=120)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "ok"


# ---- what a window's Flip X gives instead of a second mirror (row 773, check 213)

def _hands_only(ctx, second, *switches):
    """`hands-glass-only` through the real `draw_outputs`: hands in the scene,
    `ghost.2` the layer, wired to output 2's hands."""
    from test_graph_wires import _fixture
    from test_hands_node import _draw
    from test_outputs import rig as gl_rig
    from test_outputs import views

    r = gl_rig(ctx, effects=())
    r.ghost_states = {"ghost.2": second}
    r.wiring = wired_wiring(G.read_graph(_fixture("hands-glass-only")["graph"]).wiring())
    return _draw(ctx, r, views(ctx, *switches))


def test_on_a_glass_of_hands_alone_flip_x_puts_the_hands_where_a_second_mirror_did(ctx):
    old = _hands_only(ctx, GhostState(on=True, mirror=True), S(), S(scene=False))
    new = _hands_only(ctx, GhostState(on=True), S(), S(scene=False, flip_x=True))
    plain = _hands_only(ctx, GhostState(on=True), S(), S(scene=False))
    assert np.array_equal(old[0], new[0])            # the projector: not a byte

    def lit(pic):
        return pic[..., :3].sum(axis=2) > 0
    assert (lit(old[1]) != lit(plain[1])).sum() > 500            # (a flip that shows)
    assert (lit(old[1]) != lit(new[1])).sum() < 0.03 * lit(old[1]).sum()     # the rim
    # …but not the same bytes: the light stays in the hands' space under a mirror
    assert not np.array_equal(old[1], new[1])


def test_where_the_glass_also_shows_the_picture_flip_x_is_not_a_second_mirror(ctx):
    old = _hands_only(ctx, GhostState(on=True, mirror=True), S(), S())
    new = _hands_only(ctx, GhostState(on=True), S(), S(flip_x=True))
    differ = (old[1][..., :3] != new[1][..., :3]).any(axis=2)
    assert differ.mean() > 0.05                      # the picture flipped with it
