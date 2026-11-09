"""Plan 44 D5b: three undo stacks, by the owner's design of 2026-11-04.

One per `Deck`, scoped to its loadable patch, and one for the meta controller. ⌘Z goes by
where you are, never by the newest of all stacks; a load is a step on its deck's
stack. Every rig is `boot` plus deck 2 and the meta controller, as `app.main` has
them, and `frames` ticks all three.
"""

import json
from types import SimpleNamespace

import pytest
from imgui_bundle import imgui
from test_app_boundary import ORDER, Stub, _host
from test_ui_pane import _click_view
from test_ui_shell import build_rig, frame
from test_undo import DT, SETTLE, boot
from ui_driver import Driver

from hyperspace import app, lfo, routing, ui_graph, ui_kit, ui_pane, undo
from hyperspace.deck import Deck, MetaController
from hyperspace.library import LOADABLE
from hyperspace.params import part_of, part_of_id
from hyperspace.routing import Binding
from hyperspace.ui import META_SECTIONS, PAGE_KEYS


@pytest.fixture()
def rig(tmp_path):
    r = boot(tmp_path / "home")
    second = Deck.beside(r.deck, lfos=lfo.LFOs(seed=1))
    meta = MetaController(r.deck, second)
    r.lib.pointer = meta.panel_pointer
    inside = {"meta": False}
    undo.where(lambda: inside["meta"])
    yield SimpleNamespace(r=r, one=r.deck, two=second, meta=meta, inside=inside,
                          reg=r.reg, lib=r.lib)
    undo.by_hand(False)


def go(rig, n: int = SETTLE) -> None:
    """`n` frames of what undo sees: each stack ticked, on the rig's clock."""
    for _ in range(n):
        rig.r.t += DT
        for s in rig.meta.stacks:
            s.tick(rig.r.t)


def here_is_meta(rig, on: bool = True) -> None:
    rig.inside["meta"] = on


def bases(deck) -> dict:
    return deck.reg.snapshot(part="patch")


def test_there_are_three_stacks_and_they_watch_apart(rig):
    """A deck's stack holds the loadable patch's params, the meta controller's the meta
    params: every watched param is on exactly one layer's."""
    one, two, meta = rig.meta.stacks
    assert (one, two, meta) == (rig.one.undo, rig.two.undo, rig.meta.undo)
    assert len({id(one), id(two), id(meta)}) == 3
    m = {p.id for p in meta._params()}
    for u, deck in ((one, rig.one), (two, rig.two)):
        ids = {p.id for p in u._params()}
        assert ids and all(part_of(deck.reg[i]) == "patch" for i in ids)
        assert not ids & m
        # (between them, every watched param of the deck: nothing fell through)
        assert ids | m == {p.id for p in deck.reg if undo.watched(p)}
    assert all(part_of(rig.reg[i]) != "patch" for i in m)
    assert meta.reg is rig.one.meta_reg and meta.table.table is rig.one.meta_table


def test_undo_is_per_deck(rig):
    """An edit on deck 2 is a step on deck 2's stack and only there; each undo
    takes back its own deck's edit, whichever was newer."""
    a, b = rig.one.reg["view.bright"], rig.two.reg["view.bright"]
    assert a is not b
    was = (a.base, b.base)
    a.set(was[0] + 0.1)
    go(rig)
    b.set(was[1] + 0.2)
    go(rig)
    assert len(rig.one.undo.stack) == len(rig.two.undo.stack) == 1
    assert rig.one.undo.undo()                         # the older, on its own deck
    assert a.base == was[0] and b.base == was[1] + 0.2
    assert rig.two.undo.undo()
    assert b.base == was[1]


def test_edit_undo_follows_the_panels_deck_and_a_stack_stays_with_its_deck(rig):
    """⌘Z is the panel's deck's; moving the panel moves which stack it reaches,
    and moves no step: each stack stays with its `Deck`."""
    a, b = rig.one.reg["view.bright"], rig.two.reg["view.bright"]
    was = (a.base, b.base)
    a.set(was[0] + 0.1)
    b.set(was[1] + 0.2)
    go(rig)
    held = (rig.one.undo, rig.two.undo)
    rig.meta.point_panel(rig.two)
    assert (rig.one.undo, rig.two.undo) == held and undo.here() is rig.two.undo
    b.step(1)                                          # (the latch: `test_undo_latch.py`)
    go(rig)
    rig.reg["edit.undo"].fire()
    rig.reg["edit.undo"].fire()
    assert b.base == was[1] and a.base == was[0] + 0.1
    rig.meta.point_panel(rig.one)
    a.step(1)
    go(rig)
    rig.reg["edit.undo"].fire()
    rig.reg["edit.undo"].fire()
    assert a.base == was[0]


def test_the_dot_is_per_deck(rig):
    """A deck's dirty dot compares that deck's state with what that deck loaded:
    an edit on deck 2 lights deck 2's and not deck 1's, and its undo puts it out."""
    one, two = rig.one.loaded_patch.lib, rig.two.loaded_patch.lib
    name = rig.lib.list(LOADABLE)[0]
    rig.two.loaded_patch.load(name)
    go(rig)
    assert not two.is_dirty(LOADABLE) and not one.is_dirty(LOADABLE)
    rig.two.reg["view.bright"].step(5)
    go(rig)
    assert two.is_dirty(LOADABLE) and two.is_dirty("view")
    assert not one.is_dirty(LOADABLE) and not one.is_dirty("view")
    assert rig.two.undo.undo()
    assert not two.is_dirty(LOADABLE) and not two.is_dirty("view")
    rig.one.reg["view.bright"].step(5)
    go(rig)
    assert one.is_dirty(LOADABLE) and not two.is_dirty(LOADABLE)


def test_a_meta_knob_is_one_step_on_the_meta_stack(rig):
    """Many writes of a meta param inside the settle time are one step, named from
    the difference, on the meta controller's stack and no deck's. Both decks hold
    the param by reference, so both see it go back."""
    p = rig.reg["master.gain"]
    assert rig.two.reg["master.gain"] is p
    was = p.base
    here_is_meta(rig)
    undo.by_hand(True)                                 # (the person's own: the latch opens)
    for k in range(20):
        p.set(was + 0.01 * (k + 1))
        go(rig, 1)
    go(rig)
    m = rig.meta.undo
    assert [s.label for s in m.stack] == [f"{p.label} {p.fmt(was)} → {p.fmt(p.base)}"]
    assert rig.one.undo.stack == [] and rig.two.undo.stack == []
    rig.reg["edit.undo"].fire()
    assert p.base == was and m.status.startswith("undid ")
    rig.reg["edit.redo"].fire()
    assert p.base != was


@pytest.mark.parametrize("which", ["one", "two"])
def test_undo_on_either_deck_never_moves_a_meta_param(rig, which):
    """Whichever deck the panel is on, ⌘Z and its redo leave every meta param where
    it is, and so what a load, a meta edit between and a loadable patch edit did to them."""
    deck = getattr(rig, which)
    rig.meta.point_panel(deck)
    deck.reg["view.bright"].step(3)
    go(rig)
    deck.loaded_patch.load(rig.lib.list(LOADABLE)[1])
    go(rig)
    rig.reg["master.gain"].step(-3)                    # the hour-old analyzer tweak
    rig.reg["band.0.thr"].step(4)
    go(rig)
    tuned = deck.reg.snapshot(part="shared_meta")
    steps = len(rig.meta.undo.stack)
    fired = 0
    while deck.undo.stack:
        rig.reg["edit.undo"].fire()
        fired += 1
        assert fired <= 2, f"the stack isn't going down: {deck.undo.status}"   # (latched: it never would)
        assert deck.reg.snapshot(part="shared_meta") == tuned
    assert fired == 2 and deck.undo.status != "nothing to undo"
    rig.reg["edit.undo"].fire()                        # nothing left here: nothing crosses
    assert deck.undo.status == "nothing to undo" and deck.reg.snapshot(part="shared_meta") == tuned
    assert len(rig.meta.undo.stack) == steps
    rig.reg["edit.redo"].fire()
    assert deck.reg.snapshot(part="shared_meta") == tuned


@pytest.mark.parametrize("which", ["one", "two"])
def test_undo_in_a_meta_section_never_moves_a_deck(rig, which):
    """Inside a meta section ⌘Z takes back the meta edit, whichever deck the panel
    is on and however much newer that deck's edit is, and no deck moves."""
    deck = getattr(rig, which)
    rig.meta.point_panel(deck)
    p = rig.reg["hands.smooth"]
    was = p.base
    here_is_meta(rig)
    undo.by_hand(True)
    p.step(3)
    go(rig)
    here_is_meta(rig, False)                           # (and past: a pass of the mouse)
    deck.reg["view.bright"].step(3)                    # newer, and not what is meant
    go(rig)
    looks = (bases(rig.one), bases(rig.two))
    steps = (len(rig.one.undo.stack), len(rig.two.undo.stack))
    here_is_meta(rig)
    rig.reg["edit.undo"].fire()                        # the deck had the focus: latched
    assert p.base != was
    rig.reg["master.gain"].step(1)                     # one change here opens it
    go(rig)
    rig.reg["edit.undo"].fire()
    rig.reg["edit.undo"].fire()
    assert p.base == was
    assert (bases(rig.one), bases(rig.two)) == looks
    assert (len(rig.one.undo.stack), len(rig.two.undo.stack)) == steps
    rig.reg["edit.undo"].fire()                        # nothing left: says so, and crosses not
    assert rig.meta.undo.status == "nothing to undo"
    assert (bases(rig.one), bases(rig.two)) == looks


def test_a_load_is_a_step_on_its_decks_stack_and_recovers_a_mistake(rig):
    """A mistaken load is one ⌘Z, on the deck it landed on: its name, reference,
    routes, an unsaved edit before it, and nothing on the other deck."""
    two, name = rig.two, rig.lib.list(LOADABLE)[1]
    other = bases(rig.one)
    two.reg["view.bright"].step(4)
    go(rig)
    before = (bases(two), two.loaded_patch.current, [b.to_json() for b in two.table.routes()])
    n = len(two.undo.stack)
    two.loaded_patch.load(name)
    go(rig)
    assert [s.label for s in two.undo.stack][n:] == [f"load {name}"]
    assert rig.one.undo.stack == [] and rig.meta.undo.stack == []
    assert two.undo.undo() and two.undo.status == f"undid load {name}"
    assert all(undo.alike(v, before[0][k]) for k, v in bases(two).items())
    assert two.loaded_patch.current == before[1]
    assert [b.to_json() for b in two.table.routes()] == before[2]
    assert bases(rig.one) == other


def test_a_decks_undo_never_relands_the_meta_controllers_strip(rig):
    """The shared meta groups' labels are the meta controller's one strip (row 689): a
    load undone on a deck leaves the analyzer's name and reference alone, and its
    own stack puts them back."""
    lib, reg = rig.lib, rig.reg
    reg["band.1.thr"].step(4)
    lib.save_as("band", "Mine")
    go(rig)
    rig.meta.undo.clear()
    reg["scene.select"].set(3)                         # the strip moves off Mine
    go(rig)
    moved = lib.landed("band")
    assert lib.current("band") != "Mine"
    rig.one.loaded_patch.load(lib.list(LOADABLE)[2])
    go(rig)
    assert "band" not in rig.one.marks.lands() and "band" not in rig.two.marks.lands()
    assert rig.one.undo.undo()
    assert lib.landed("band") == moved                 # a deck's undo: no reland
    assert rig.meta.undo.undo() and lib.current("band") == "Mine"
    assert not lib.is_dirty("band")


def test_the_shows_mark_is_on_the_meta_stack(rig):
    """A show load is the meta controller's: undone in a meta section the show comes
    back and no deck moves; the startup loadable patch is a load on the panel's deck and
    undoes there, leaving the show where it is. The file's bank is never rewound."""
    pr, one = rig.lib.install, rig.one
    assert pr.name == "party"
    assert pr.bank not in one.marks.take()[0]          # a deck's mark holds no bank
    pr.load("house")
    go(rig)
    assert [s.label for s in rig.meta.undo.stack] == ["install house"]
    assert [s.label for s in one.undo.stack] == [f"load {pr.startup}"]
    assert rig.two.undo.stack == []
    look = bases(one)
    here_is_meta(rig)
    rig.reg["edit.undo"].fire()                        # the latch: the deck had the focus
    assert pr.name == "house" and "make a change on the meta controller" in rig.meta.undo.status
    undo.by_hand(True)
    rig.reg["hands.smooth"].step(1)
    go(rig)
    rig.reg["edit.undo"].fire()
    rig.reg["edit.undo"].fire()
    assert pr.name == "party" and bases(one) == look
    here_is_meta(rig, False)
    assert one.undo.stack
    one.reg["view.bright"].step(1)
    go(rig)
    rig.reg["edit.undo"].fire()
    rig.reg["edit.undo"].fire()
    assert one.loaded_patch.current == "TUMBLE" and pr.name == "party"


def test_the_meta_controllers_rows_are_a_step_and_their_undo_writes_their_file(rig):
    """A row of `bindings.json` is the meta controller's: learning or removing one
    is a step on its stack, undone in every deck's table and in the file, which is
    where the row lives. No deck's stack sees it."""
    t1, t2 = rig.one.table, rig.two.table
    meta_table = t1.meta_table
    path = meta_table.path
    row = Binding("key:F13", "view.points", "toggle")
    assert routing.is_meta_row(row)
    t1.add(row)
    t1.write()
    go(rig)
    m = rig.meta.undo
    assert [s.label for s in m.stack] == ["rows"]
    assert rig.one.undo.stack == [] and rig.two.undo.stack == []
    assert any(b is row for b in t2.bindings)
    assert "F13" in path.read_text()
    desk = (t1.desk_serial, [b.to_json() for b in t1.desk()], [b.to_json() for b in t2.desk()])
    assert m.undo()
    assert not any(b.source == "key:F13" for t in (t1, t2) for b in t.bindings)
    assert "F13" not in path.read_text()
    assert desk == (t1.desk_serial, [b.to_json() for b in t1.desk()],
                    [b.to_json() for b in t2.desk()])
    go(rig, 5)
    assert m.stack == [] and len(m.redos) == 1         # the restore's frames are no gesture
    assert m.redo()
    assert all(any(b.source == "key:F13" for b in t.bindings) for t in (t1, t2))
    assert "F13" in path.read_text() and "bindings" in json.loads(path.read_text())


def test_a_corpus_walk_a_decks_stack_holds_no_meta_param(rig):
    """Every corpus loadable patch loaded on each deck, every step's state read: no base of
    a meta param on a deck's stack, no base of a loadable patch's on the meta stack, and the
    walk makes no step on the meta stack at all."""
    names = rig.lib.list(LOADABLE)
    assert len(names) > 3
    for deck in (rig.one, rig.two):
        for name in names:
            deck.loaded_patch.load(name)
            go(rig, 3)
        go(rig)
        assert len(deck.undo.stack) >= len(names) - 1
        for s in deck.undo.stack:
            # (by id: a param an older loadable patch's graph declared may be gone by now)
            bad = [k for k in s.before.bases if part_of_id(k) != "patch"]
            assert not bad, (s.label, bad[:5])
            assert s.before.rows == ()
            assert "band" not in s.before.marks[1] if s.before.marks else True
    assert rig.meta.undo.stack == []
    m = {p.id for p in rig.meta.undo._params()}
    assert m and all(part_of_id(k) == "shared_meta" for k in m)


def test_the_frame_ticks_all_three():
    """`app.frame` ticks every stack where it ticked the one, in the documented
    place; one that raises is said and does not cost the others their tick."""
    log: list[str] = []
    h = _host(log)
    h.stacks = tuple(Stub(n, log) for n in ("deck1", "deck2", "meta"))
    assert app.frame(h, now=1.0, dt=1 / 60, fps=60.0) is True
    want = [s for s in ORDER if s != "undo.tick"]
    at = want.index("output.apply")
    want[at:at] = ["deck1.tick", "deck2.tick", "meta.tick"]
    assert log == want
    log.clear()

    def boom(now):
        raise RuntimeError("no")

    h.stacks[0].tick = boom
    assert app.frame(h, now=2.0, dt=1 / 60, fps=60.0) is False
    assert "deck2.tick" in log and "meta.tick" in log


def test_the_chase_and_a_turn_stay_on_the_decks_stack(rig):
    """The base chase and an orbit's step are a deck's, on deck 2 as on deck 1: the
    deck the performer writes keeps the step, and `watching` finds it."""
    assert undo.watching(rig.one.reg) is rig.one.undo
    assert undo.watching(rig.two.reg) is rig.two.undo
    assert undo.watching(rig.one.meta_reg) is rig.meta.undo
    assert rig.two.chase(True)
    assert rig.two.undo._kept is not None and rig.one.undo._kept is None
    assert rig.meta.undo._kept is None
    assert not rig.two.chase(False)
    assert rig.two.undo._kept is None


# ---------------------------------------------------- where you are, in the panel

@pytest.fixture()
def pane(tmp_path, monkeypatch):
    with build_rig(tmp_path) as r:
        r.panel.desk = False
        imgui.get_io().display_size = imgui.ImVec2(1600, 900)
        frame(r.panel, "graph")
        d = Driver(step=lambda: frame(r.panel))
        d.record(monkeypatch.setattr)
        d.run(d.wait(2))
        yield r, d


def test_the_meta_sections_are_named_and_exist():
    """The owner's three, and audio, which holds the master faders (row 692)."""
    assert {"analyzer", "hands", "output"} <= set(META_SECTIONS)
    assert set(META_SECTIONS) <= set(PAGE_KEYS)
    assert not {"view", "graph", "routing", "lfo", "loadable"} & set(META_SECTIONS)


def test_where_you_are_is_the_section_under_the_mouse(pane):
    """Driven with the mouse: over a meta section's body it is meta; over
    another section's it is not; over the chips above them, nothing."""
    r, d = pane
    st = ui_graph._state(r.panel)
    p = r.panel
    d.run(_click_view(d, "analyzer"), d.wait(1))
    assert st["pane_drawn"] == ["analyzer"]
    d.run(d.reveal("scene.select"))
    x0, y0, _x1, _y1 = d.rect("scene.select")          # its top: the pane may clip its bottom
    d.run(d.move((x0 + 4, y0 + 3)), d.wait(1))
    assert ui_pane.where(p) == "analyzer" and p.in_meta_section()
    d.run(d.click("pane.loadable"), d.park(), d.wait(1))
    new = "strip.loadable:new" if ui_kit.ready() else "new##new"     # (ui_strip on the kit)
    d.run(d.move(new), d.wait(1))                       # the loadable patches section
    assert ui_pane.where(p) == "loadable" and not p.in_meta_section()
    d.run(d.move("pane.sections"), d.wait(1))
    assert ui_pane.where(p) is None


def test_the_panel_says_when_the_person_is_working_it(pane):
    """The real panel, by the mouse: a move is nothing; a press, and the frame of its
    release, is the person's own; the frame after is nothing again (row 753)."""
    _r, d = pane
    d.run(d.move("pane.sections"), d.wait(2))
    assert not undo._hand
    d.run(d.press(True), d.wait(1))
    assert undo._hand
    d.run(d.press(False), d.wait(1))
    d.run(d.wait(2))
    assert not undo._hand


def test_the_focus_never_says_where_you_are(pane):
    """A key row or a pad focused the analyzer, or a click did an hour ago, and the
    mouse is off the panel, on the desk or in the render window: the deck."""
    r, d = pane
    p = r.panel
    d.run(d.park(), d.wait(1))
    frame(p, "analyzer")
    assert ui_pane.showing(p) == "analyzer"
    d.run(d.move((-50.0, -50.0)), d.wait(2))
    assert ui_pane.where(p) is None and not p.in_meta_section()
    assert undo.here() is undo.installed()


def _drawn_params(r, d, part: str) -> list[str]:
    """Ids of the params undo watches, of one layer, drawn last frame."""
    ids = {k.rpartition("##")[2] for k in d.rects}
    return sorted(k for k in ids if k in r.reg and undo.watched(r.reg[k])
                  and part_of(r.reg[k]) == part)


def test_a_param_under_the_mouse_says_by_its_own_layer_in_a_mixed_section(pane):
    """The hands section is a meta section that also draws the loadable patch's params: the
    param under the mouse decides, and off every param the section does."""
    r, d = pane
    p = r.panel
    frame(p, "hands")
    d.run(d.wait(2))
    meta, loadable = _drawn_params(r, d, "shared_meta"), _drawn_params(r, d, "patch")
    assert meta and loadable, (meta[:5], loadable[:5])
    d.run(d.reveal(meta[0]), d.move(meta[0]), d.wait(2))
    assert p._param_under is r.reg[meta[0]] and p.in_meta_section()
    d.run(d.reveal(loadable[0]), d.move(loadable[0]), d.wait(2))
    assert p._param_under is r.reg[loadable[0]] and not p.in_meta_section()


def test_a_meta_param_in_a_decks_section_takes_the_meta_stack(pane):
    """SYSTEM is no meta section and draws `desk.slew`: over it, meta; off it, the deck."""
    r, d = pane
    p = r.panel
    frame(p, "system")
    d.run(d.reveal("desk.slew"), d.move("desk.slew"), d.wait(2))
    assert p.in_meta_section()
    d.run(d.move((-50.0, -50.0)), d.wait(2))
    assert not p.in_meta_section()


def test_a_param_undo_does_not_watch_leaves_it_to_the_section(pane):
    """`band.sel.*` are aliases: over one in the analyzer section, the section says."""
    r, d = pane
    p = r.panel
    frame(p, "analyzer")
    d.run(d.move("band.sel.thr"), d.wait(2))
    assert p._param_under is not None and not undo.watched(p._param_under)
    assert p.in_meta_section()


def test_the_canvas_is_the_panels_deck_whatever_has_the_focus(pane):
    r, d = pane
    p = r.panel
    frame(p, "analyzer")
    (x, y), _size = ui_graph._state(p)["details_rect"]
    d.run(d.move((x - 200, y + 200)), d.wait(2))       # left of the pane: the canvas
    assert ui_pane.where(p) is None and not p.in_meta_section()


def test_a_selected_meta_node_s_param_takes_the_meta_stack(pane):
    """The selection section shows a node's params: over a meta one of a fixture node
    it is the meta stack, though the selection is no meta section."""
    r, d = pane
    p = r.panel
    view = ui_graph.view_of(p)

    def metas(n):
        return [k for _g, pids in ui_graph.side_groups(p, n)[:1] for k in pids
                if undo.watched(r.reg[k]) and part_of(r.reg[k]) == "shared_meta"]

    node = next((n for n in view.nodes if metas(n)), None)
    assert node is not None, sorted({n.kind for n in view.nodes})
    p.select_graph_node(node.id)
    d.run(d.wait(3))
    st = ui_graph._state(p)
    assert "selection" in st["pane_drawn"]
    meta = metas(node)
    d.run(d.reveal(meta[0]), d.move(meta[0]), d.wait(2))
    assert ui_pane.where(p) == "selection" and p.in_meta_section()


def test_the_footer_says_whichever_stack_spoke_last(tmp_path):
    """The message slot reads both stacks: an undo in a meta section is said, as a
    deck's is."""
    from hyperspace.ui import Panel

    deck_u = SimpleNamespace(status="undid a", said_at=1.0)
    meta_u = SimpleNamespace(status="", said_at=0.0)
    p = SimpleNamespace(undo=deck_u, meta_undo=meta_u, learn=None,
                        library=SimpleNamespace(status="", warning="", said={}))
    assert Panel._message(p, now=0.0) == ("", False)   # its first look only remembers
    meta_u.status, meta_u.said_at = "undid b", 2.0
    assert Panel._message(p, now=0.5)[0] == "undid b"
    deck_u.status, deck_u.said_at = "undid c", 3.0
    assert Panel._message(p, now=0.6)[0] == "undid c"


def test_the_footer_follows_the_panels_deck(rig):
    """`Panel.undo` reads through the panel's pointer: moved to deck 2, its stack's
    words reach the footer; what deck 2 said before the move does not."""
    from hyperspace.ui import Panel

    two = rig.two
    two.undo._say("old words")
    p = Panel.__new__(Panel)
    p.library = SimpleNamespace(status="", warning="", said={})
    p.meta_undo = rig.meta.undo
    p.pointer = rig.meta.panel_pointer
    rig.r.t += 10.0
    go(rig, 1)
    rig.one.undo._say("deck 1 said")
    Panel._message(p, now=100.0)
    rig.meta.point_panel(two)
    assert p.undo is two.undo
    assert Panel._message(p, now=100.1)[0] != "old words"
    two.undo._now = rig.r.t + 5.0
    two.undo.undo()
    assert Panel._message(p, now=100.2)[0] == "nothing to undo"


def test_a_where_that_raises_is_not_inside_a_meta_section(rig):
    def boom():
        raise RuntimeError("no")

    undo.where(boom)
    assert undo.here() is rig.one.undo
    rig.reg["edit.undo"].fire()                        # says so; no raise
    assert rig.one.undo.status == "nothing to undo here yet: make a change on deck 1 first"


def test_a_decks_step_across_a_show_change_that_changes_nothing_of_it_drops(rig):
    """A deck's marks name the show only for its layout: a step whose `put` would
    change nothing is no step, whatever the show is called now. `Install.new` on a
    deck already at fresh values leaves "undid new show" unsaid."""
    pr, one = rig.lib.install, rig.one
    pr.new("first")
    go(rig)
    one.undo.clear()
    rig.meta.undo.clear()
    pr.new("second")
    go(rig)
    assert pr.name == "second"
    assert [s.label for s in one.undo.stack] == []     # nothing of the deck moved
    assert [s.label for s in rig.meta.undo.stack] == ["new install"]
    assert one.undo.undo() is False


def test_undoing_a_tidys_positions_stays_within_one_show(rig):
    """The same show: positions go back. Another show: they are not landed on it."""
    pr, one = rig.lib.install, rig.one
    pr.layout["lfo.1"] = [1, 2]
    go(rig)
    undo.push("tidy", load=True)
    pr.layout["lfo.1"] = [9, 9]
    rig.one.reg["view.bright"].step(1)                 # (so the step has something)
    go(rig)
    assert one.undo.undo() and pr.layout["lfo.1"] == [1, 2]
    assert one.undo.redo() and pr.layout["lfo.1"] == [9, 9]
    assert one.undo.undo()
    undo.push("tidy", load=True)
    pr.layout["lfo.1"] = [7, 7]
    rig.one.reg["view.bright"].step(1)
    go(rig)
    pr.name = "another"
    assert one.undo.undo() and pr.layout["lfo.1"] == [7, 7]


def test_the_meta_table_has_no_decks_table_face():
    """`deck.MetaRows` is what `Undo` reads; `MetaTable` holds rows, and nothing
    on it pretends to be a deck's table."""
    from hyperspace.routing import MetaTable

    for name in ("bindings", "routes", "desk", "macros", "macros_doc"):
        assert not hasattr(MetaTable, name), name
