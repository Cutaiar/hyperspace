# ruff: noqa: F811 — the fixture fake is test_app_boundary's, taken as an argument
"""Plan 44 D5a: `deck.MetaController` owns the two `Deck`s and a pointer per holder.

Everything in the app stays on deck 1 (the D1 and D2 same-state tests, the
frame's ORDER says nothing moved); here each handle is moved
to deck 2 by hand, and no row or base crosses.
"""

import ast
import inspect
from types import SimpleNamespace

import pytest
from test_app_boundary import ORDER, Stub, _host, fake  # noqa: F401 — `fake` is a fixture
from test_deck import _compare, _walk
from test_midi import cc, note
from test_undo import boot

from hyperspace import (
    apc40,
    app,
    bridge,
    devices,
    lfo,
    library,
    poi,
    preset,
    seq_page,
    totem,
    undo,
)
from hyperspace.deck import KEYS, MOUSE, Deck, MetaController
from hyperspace.hotreload import MODULES
from hyperspace.library import PRESETS
from hyperspace.pointer import Pointer, Through
from hyperspace.routing import Binding
from hyperspace.ui import Panel

DESK = "apc40"
PANEL_HANDLES = ("reg", "view", "renderer", "router", "learn", "undo", "lfos", "envs", "seq")


def _pointed(r) -> SimpleNamespace:
    """`boot` plus deck 2, and every holder there is headless given its
    pointer, as `app.main` does: all on deck 1."""
    second = Deck.beside(r.deck, lfos=lfo.LFOs(seed=1))
    meta = MetaController(r.deck, second)
    r.meta_undo = meta.undo                # (`boot`'s stood in until there was a meta controller)
    r.lib.pointer = meta.panel_pointer
    r.midi.point(meta.pointer(DESK), meta.panel_pointer)
    return SimpleNamespace(r=r, meta=meta, one=r.deck, two=second)


@pytest.fixture()
def rig(tmp_path):
    yield _pointed(boot(tmp_path / "home"))
    undo.install(None)


def _look(deck) -> dict:
    """What a preset is, on one deck: nothing here may move when the other acts."""
    t = deck.table
    return {"bases": deck.reg.snapshot(part="patch"),
            "routes": [b.to_json() for b in t.routes()],
            "desk": [b.to_json() for b in t.desk()],
            "name": deck.presets.current,
            "landing": deck.presets.landing[1],
            "labels": dict(deck.presets.labels),
            "lit": deck.presets.active_slot,
            "steps": [s.label for s in deck.undo.stack]}


def _panel(rig) -> Panel:
    """A `Panel` with no imgui: its handles as `main` assigns them, then its pointer."""
    one = rig.one
    panel = Panel.__new__(Panel)
    panel.reg, panel.view, panel.renderer = one.reg, one.view, one.renderer
    panel.router, panel.learn, panel.undo = one.router, one.learn, one.undo
    panel.lfos, panel.envs, panel.seq = one.lfos, one.envs, one.seq
    panel.deck, panel.library = one, rig.r.lib
    panel.pointer = rig.meta.panel_pointer
    return panel


def _send(rig, *msgs) -> None:
    rig.r.inp.queue.extend(msgs)
    rig.r.midi.poll()


# ---- the seam

def test_exactly_two_decks_and_every_pointer_starts_on_the_first(rig):
    meta, one, two = rig.meta, rig.one, rig.two
    assert meta.decks == (one, two)
    assert meta.on_air is one and meta.off_air is two and meta.panel is one
    assert meta.pointer("anything").deck is one
    assert list(inspect.signature(MetaController).parameters) == ["first", "second", "players",
                                                                    "mix"]
    assert not hasattr(meta, "swap")                 # on air is the crossfader's, D5c
    with pytest.raises(ValueError, match="not one of its two"):
        meta.point("pad", SimpleNamespace())
    with pytest.raises(ValueError, match="not one of its two"):
        meta.point_panel(SimpleNamespace())


def test_each_holder_moves_on_its_own_and_the_panel_apart(rig):
    meta, one, two = rig.meta, rig.one, rig.two
    meta.point("pad", two)
    assert meta.pointer("pad").deck is two
    assert meta.pointer("pad2").deck is one and meta.pointer(DESK).deck is one
    assert meta.pointer(KEYS).deck is one and meta.pointer(MOUSE).deck is one
    assert meta.panel is one and meta.on_air is one and undo.installed() is one.undo
    assert meta.pointer("pad") is meta.pointer("pad")        # one per name: it outlasts a cable
    meta.point("pad", one)
    meta.point_panel(two)
    assert meta.panel is two and undo.installed() is two.undo
    assert all(p.deck is one for p in meta.pointers.values()) and meta.on_air is one
    told = []
    meta.on_panel.append(told.append)
    meta.point_panel(one)
    assert told == [one] and undo.installed() is one.undo


def test_through_is_an_attribute_until_it_has_a_pointer_then_refuses_a_write():
    class Holder:
        reg = Through("reg")
        deck = Through(None)

    deck = SimpleNamespace(reg="the deck's")
    h = Holder()
    assert not hasattr(h, "reg")                 # as an attribute never set
    h.reg = "assigned"
    assert h.reg == "assigned"
    h.pointer = Pointer(deck)
    assert h.reg == "the deck's" and h.deck is deck
    with pytest.raises(AttributeError, match="move the pointer"):
        h.reg = "ignored"
    assert isinstance(Holder.reg, Through)


def test_the_host_takes_its_flat_fields_and_reads_through_once_pointed():
    log: list[str] = []
    h = _host(log)
    flat = h.reg
    assert h.on_air_pointer is None and h.reg is flat
    on_air = SimpleNamespace(reg="air", view="v", router="r", lfos="l", renderer="d")
    panel = SimpleNamespace(learn="L", undo="U")
    h.on_air_pointer, h.panel_pointer = Pointer(on_air), Pointer(panel)
    assert (h.reg, h.view, h.router, h.lfos, h.renderer) == ("air", "v", "r", "l", "d")
    assert h.deck is on_air and (h.learn, h.undo) == ("L", "U")


# ---- the proof: each handle at deck 2, no row or base crosses

def test_pointing_the_panel_at_deck_2_sends_every_panel_handle_there(rig):
    meta, one, two = rig.meta, rig.one, rig.two
    panel, lib = _panel(rig), rig.r.lib
    for h in PANEL_HANDLES:
        assert getattr(panel, h) is getattr(one, h), h
    assert panel.deck is one and lib.presets is one.presets and lib.reg is one.reg
    meta.point_panel(two)
    for h in PANEL_HANDLES:
        assert getattr(panel, h) is getattr(two, h), h
    assert panel.deck is two and lib.presets is two.presets and lib.reg is two.reg
    assert undo.installed() is two.undo
    # the controllers and the outputs stayed: the desk's rows; only its learn follows
    assert rig.r.midi.reg is one.reg and rig.r.midi.table is one.table
    assert rig.r.midi.learner is two.learn
    assert meta.on_air is one


def test_what_the_panel_does_on_deck_2_stays_on_deck_2(rig):
    """A load, a base, a route, ⌘Z, a group's reset: the panel's verbs by their roads."""
    meta, one, two, lib = rig.meta, rig.one, rig.two, rig.r.lib
    before = _look(one)
    assert before["name"] is not None
    meta.point_panel(two)
    other = next(n for n in sorted(lib.list(PRESETS)) if n != before["name"])
    lib.load(PRESETS, other)                               # the strip's road
    assert two.presets.current == other and lib.current(PRESETS) == other
    assert two.undo.stack[-1].label.startswith("load")
    assert _look(one) == before
    assert one.marks.lands()[PRESETS][0] == before["name"]    # deck 1's marks read deck 1
    assert two.marks.lands()[PRESETS][0] == other
    # a base, and a route added on the deck the panel is on
    bright = two.reg["view.bright"]
    bright.set(bright.lo + 0.123)
    two.table.add(Binding("lfo:0", "view.pattern_mix", "push", value=0.5))
    assert _look(one) == before
    # a group's reset, the library's road (the `pattern` strip's Reset), writes `lib.reg`
    pattern = two.reg["view.pattern_mix"]
    lib.reset("pattern")
    assert _look(one) == before and pattern is two.reg["view.pattern_mix"]
    # ⌘Z: the installed undo is the panel's deck's
    undo.undo()
    assert two.presets.current != other
    assert _look(one) == before


def test_a_deck_s_own_verbs_land_on_that_deck_wherever_the_panel_is(rig):
    """`Presets.load` / `save_as` / `Library.load(into=)`, the panel on deck 1."""
    meta, one, two, lib = rig.meta, rig.one, rig.two, rig.r.lib
    before = _look(one)
    names = [n for n in sorted(lib.list(PRESETS)) if n != before["name"]]
    two.presets.load(names[0])
    assert two.presets.current == names[0] and _look(one) == before
    assert lib.current(PRESETS) == before["name"]          # the strip still says deck 1's
    assert undo.installed() is one.undo and two.undo.stack
    assert lib.presets is one.presets and two.presets.lib.presets is two.presets
    # a save on deck 2 writes deck 2's look
    p = two.reg["view.bright"]
    p.set(p.lo + 0.2345)
    two.presets.save_as("deck-two-look")
    assert lib.read(PRESETS, "deck-two-look")["values"]["view.bright"] == pytest.approx(p.base)
    assert two.presets.current == "deck-two-look"
    assert meta.panel is one and _look(one)["bases"] == before["bases"]


def test_the_desk_on_deck_2_moves_deck_2_and_keeps_its_rows_there(rig):
    meta, one, two, midi = rig.meta, rig.one, rig.two, rig.r.midi
    mine, other = one.reg["view.pattern_mix"], two.reg["view.pattern_mix"]
    assert mine is not other
    one.table.add(Binding("cc:0:60", "view.pattern_mix", "abs", layer="preset", pickup=False))
    two.table.add(Binding("cc:0:61", "view.pattern_mix", "abs", layer="preset", pickup=False))
    mine.set_norm(0.0)
    other.set_norm(0.0)
    _send(rig, cc(60, 127))
    midi._land_all()
    assert mine.norm > 0.5 and other.norm == 0.0            # deck 1's row, deck 1's base
    landed, before = mine.norm, _look(one)
    meta.point(DESK, two)
    assert midi.reg is two.reg and midi.table is two.table
    _send(rig, cc(60, 0))                                    # deck 1's row is not on deck 2
    midi._land_all()
    assert other.norm == 0.0 and mine.norm == landed
    _send(rig, cc(61, 127))                                  # deck 2's own
    midi._land_all()
    assert other.norm > 0.5 and mine.norm == landed
    assert _look(one) == before


def test_a_desk_moved_mid_gesture_leaves_nothing_of_the_deck_it_left(rig):
    """A glide in flight and a note down: gone at the first look after the
    move, so the glide does not step and the release does not fire on the new deck."""
    meta, one, two, midi = rig.meta, rig.one, rig.two, rig.r.midi
    one.table.add(Binding("cc:0:60", "view.pattern_mix", "abs", layer="preset", pickup=False))
    one.table.add(Binding("note:0:70", "view.lines", "toggle", layer="preset"))
    one.table.slew = 1.0
    _send(rig, cc(60, 127), note(70))
    assert midi._held and midi._slews
    other_was = two.reg["view.pattern_mix"].base, two.reg["view.lines"].base
    meta.point(DESK, two)
    _send(rig, note(70, 0))
    assert midi._held == {} and "view.pattern_mix" not in midi._slews
    assert (two.reg["view.pattern_mix"].base, two.reg["view.lines"].base) == other_was


def test_the_first_desk_carries_the_sequencer_page(rig):
    """`SeqPage.reg` was kept at first registration, and the page is one
    object on both tables: it reads the deck the first desk is on."""
    meta, one, two = rig.meta, rig.one, rig.two
    page = seq_page.of(one.reg)
    assert page is not None and page is seq_page.of(two.reg)   # the session's, from either
    assert page.reg is one.reg
    meta.point(DESK, two)
    assert page.reg is two.reg


def test_a_learn_armed_on_the_panels_deck_lands_in_its_table(rig):
    """The desk stays on deck 1; the learn is the panel's, and so is its row."""
    meta, one, two, midi = rig.meta, rig.one, rig.two, rig.r.midi
    meta.point_panel(two)
    before = _look(one)
    midi.learner.arm("view.inst_amp")
    assert two.learn.learning == "view.inst_amp" and one.learn.learning is None
    _send(rig, cc(99, 64), cc(99, 90))
    assert [b for b in two.table.bindings if b.target == "view.inst_amp" and "99" in b.source]
    assert _look(one) == before


def test_a_bank_pad_on_deck_2_loads_on_deck_2_and_its_light_is_deck_2s(rig):
    """A row fires on deck 2's table, so what it does lands there: a load and
    a save by the bank's own road, not the panel's deck."""
    meta, one, two, lib = rig.meta, rig.one, rig.two, rig.r.lib
    bank = lib.project.bank
    k = next(i for i, n in enumerate(bank[:8]) if n and n != one.presets.current)
    two.table.add(Binding("note:0:71", f"preset.load.{k}", "fire"))     # (the meta controller's)
    meta.point(DESK, two)
    before = _look(one)
    _send(rig, note(71), note(71, 0))
    assert two.presets.current == bank[k] and two.presets.active_slot == k
    assert _look(one) == before and lib.current(PRESETS) == before["name"]
    assert lib.project.active == before["lit"]               # the panel's view: deck 1's slot


def test_a_save_on_deck_2_captures_deck_2(rig):
    one, two, lib = rig.one, rig.two, rig.r.lib
    two.presets.load(next(n for n in sorted(lib.list(PRESETS)) if n != one.presets.current))
    p = two.reg["view.bright"]
    p.set(p.lo + 0.3456)
    before, listed = _look(one), set(lib.list(PRESETS))
    two.reg["preset.save_new"].fire()
    (saved,) = set(lib.list(PRESETS)) - listed
    assert lib.read(PRESETS, saved)["values"]["view.bright"] == pytest.approx(p.base)
    assert two.presets.current == saved and _look(one) == before
    assert lib.current(PRESETS) == before["name"]


def test_the_sequencer_page_goes_with_the_desk(rig):
    """`Bindings.page` is the session's: SEND A works with the desk on deck 2, a
    page up stays up across a move, and its steps land on the desk's deck."""
    meta, one, two, midi = rig.meta, rig.one, rig.two, rig.r.midi
    meta.point(DESK, two)
    page = seq_page.of(two.reg)
    _send(rig, note(apc40.N_SEND_A), note(apc40.N_SEND_A, 0))
    assert seq_page.page_of(two.table) is page and seq_page.page_of(one.table) is page
    assert midi._page_rows()
    step, other = two.reg["seq.1.1"], one.reg["seq.1.1"]
    assert step is not other
    was, was_other = step.base, other.base
    _send(rig, note(apc40.N_CLIP[0]), note(apc40.N_CLIP[0], 0))
    assert step.base != was and other.base == was_other
    meta.point(DESK, one)
    midi.poll()
    assert seq_page.page_of(one.table) is page and page.reg is one.reg


def test_a_release_after_a_desk_moved_goes_nowhere_on_the_new_deck(rig):
    """A press on deck 1, the desk moved, the note-off: the control's `momentary`
    row on deck 2 does not hear a release, so its latched toggle stays on."""
    meta, one, two, midi = rig.meta, rig.one, rig.two, rig.r.midi
    one.table.add(Binding("note:0:70", "view.lines", "toggle", layer="preset"))
    two.table.add(Binding("note:0:70", "view.lines", "momentary", layer="preset"))
    two.reg["view.lines"].set(True)
    _send(rig, note(70))
    meta.point(DESK, two)
    _send(rig, note(70, 0))
    assert two.reg["view.lines"].value is True
    assert midi._held == {}                                  # that release spent its key
    _send(rig, note(70), note(70, 0))                         # the next press is the new deck's
    assert two.reg["view.lines"].value is False


def test_a_momentary_held_when_the_desk_moves_is_let_go_on_the_deck_it_held(rig):
    meta, one, two = rig.meta, rig.one, rig.two
    one.table.add(Binding("note:0:70", "view.lines", "momentary", layer="preset"))
    one.reg["view.lines"].set(False)
    two.reg["view.lines"].set(True)
    _send(rig, note(70))
    assert one.reg["view.lines"].value is True
    meta.point(DESK, two)
    rig.r.midi.poll()
    assert one.reg["view.lines"].value is False and two.reg["view.lines"].value is True


def test_a_session_fader_keeps_its_catch_across_a_move(rig):
    """A session param is one object on both decks: the fader on it is still caught."""
    meta, one, two, midi = rig.meta, rig.one, rig.two, rig.r.midi
    gain = one.reg["output.dim"]
    assert two.reg["output.dim"] is gain
    gain.set_norm(0.5)
    midi.poll()
    one.table.add(Binding("cc:0:60", "view.pattern_mix", "abs", layer="preset", pickup=False))
    row = next(b for b in midi.table.bindings if b.source == "cc:0:14")      # MASTER's
    at = round(gain.norm * 127)
    _send(rig, cc(14, at), cc(14, at + 1), cc(60, 90))
    midi._land_all()
    assert row.caught is True
    assert "output.dim" in midi._writes and "view.pattern_mix" in midi._writes
    meta.point(DESK, two)
    midi.poll()
    assert "output.dim" in midi._writes and "view.pattern_mix" not in midi._writes
    assert row.caught is True                                # the same row on both tables
    was = gain.norm
    _send(rig, cc(14, at + 3))
    midi._land_all()
    assert gain.norm > was                                   # no re-catch to wait for


def test_deck_2s_load_leaves_deck_1s_labels_and_light(rig):
    """The panel on deck 1: `deck2.presets.load` touches none of what its strip reads."""
    one, two, lib = rig.one, rig.two, rig.r.lib
    labels, lit = {g: lib.landed(g) for g in lib.landed_groups()}, lib.project.active
    dots = {g: lib.is_dirty(g) for g in ("view", "pattern")}
    two.presets.load(next(n for n in sorted(lib.list(PRESETS)) if n != one.presets.current))
    assert {g: lib.landed(g) for g in lib.landed_groups()} == labels
    assert lib.project.active == lit and one.presets.active_slot == lit
    assert {g: lib.is_dirty(g) for g in dots} == dots
    # deck 2's undo of that load: nothing of deck 1's either
    two.undo.undo()
    assert {g: lib.landed(g) for g in lib.landed_groups()} == labels
    assert lib.project.active == lit


def test_each_deck_keeps_its_own_section_references(rig):
    """A load with the panel on deck 2, then back on deck 1: its strip names
    and its dots compare against what deck 1 loaded, never deck 2's."""
    meta, one, two, lib = rig.meta, rig.one, rig.two, rig.r.lib
    ref = lib.landed("view")
    dirty = lib.is_dirty("view")
    meta.point_panel(two)
    lib.load(PRESETS, next(n for n in sorted(lib.list(PRESETS)) if n != one.presets.current))
    assert two.presets.labels["view"][1] is not ref[1]
    meta.point_panel(one)
    assert lib.landed("view") == ref and lib.is_dirty("view") == dirty
    assert one.marks.lands()["view"] == ref and two.marks.lands()["view"] != ref


def test_a_new_preset_on_deck_2_stays_on_deck_2(rig):
    one, two, lib = rig.one, rig.two, rig.r.lib
    before = _look(one)
    two.presets.new()
    assert two.presets.current == preset.UNTITLED_PRESET and two.undo.stack
    assert _look(one) == before and lib.current(PRESETS) == before["name"]


def test_nothing_of_a_deck_s_view_is_a_second_copy(rig):
    """`DeckLibrary` and `DeckProject` hold the one library's and show's state;
    only which deck differs, and a hot reload can re-class them."""
    one, two, lib = rig.one, rig.two, rig.r.lib
    view = two.presets.lib
    assert view.base is lib and view.__dict__ is lib.__dict__
    assert view.project.__dict__ is lib.project.__dict__ and view.project.bank is lib.project.bank
    assert view.presets is two.presets and view.reg is two.reg
    assert view.project.lib is view and lib.project.lib is lib
    assert one.presets.lib.presets is one.presets
    lib.status = "said"
    assert view.status == "said"
    new_view = type("DeckLibrary", (library.Library,), {"__slots__": library.DeckLibrary.__slots__})
    new_bank = type("DeckProject", (library.Project,), {"__slots__": library.DeckProject.__slots__})
    bank = view.project
    view.__class__ = new_view
    bank.__class__ = new_bank
    assert view.__dict__ is lib.__dict__ and bank.lib is view


class _Pad:
    """Every button held, pressed or let go together, as the test says; sticks at rest."""

    on, hat = True, 0
    dt_hint = 0.0
    is_down, was_down = True, False

    def poll(self):
        pass

    def lanes(self):
        return None

    def down(self, _b):
        return self.is_down

    def pressed(self, _b):
        return self.is_down and not self.was_down

    def released(self, _b):
        return self.was_down and not self.is_down

    def hat_pressed(self, _bit):
        return False

    hat_released = hat_pressed

    def axis(self, _i):
        return 0.0

    def trigger(self, _i):
        return 0.0


def test_the_pad_on_deck_2_fires_deck_2s_rows_on_deck_2(rig):
    """Each controller its own pointer: a row on each deck, the pad on the second."""
    meta, one, two = rig.meta, rig.one, rig.two
    one.table.add(Binding("pad:RP", "view.lines", "toggle", layer="preset"))
    two.table.add(Binding("pad:LP", "view.lines", "toggle", layer="preset"))
    pad = devices.PadDevice("pad", None, devices.Context(reg=one.reg, table=one.table), io=_Pad())
    registry = devices.DeviceRegistry(devices=[pad])
    registry.point(meta.pointer, meta.panel_pointer)
    assert pad.pointer is meta.pointer("pad") and pad.reg is one.reg
    meta.point("pad", two)
    assert pad.reg is two.reg and pad.table is two.table
    assert registry.table_of("pad") is two.table
    before, was = _look(one), two.reg["view.lines"].base
    registry.poll(1 / 60, 1.0, router=one.router)            # the frame's: for one unpointed
    assert not registry.error
    assert two.reg["view.lines"].base != was
    assert _look(one) == before


def _pad_frame(registry, one, io, *, down: bool) -> None:
    io.was_down, io.is_down = io.is_down, down
    registry.poll(1 / 60, 1.0, router=one.router)
    assert not registry.error


def test_a_pad_moved_mid_press_lets_go_on_the_deck_it_left_and_not_on_the_new(rig):
    """What `_follow_pointer` gives the desk: the old router's held toggle goes, and
    the release on the new deck, of a press it never heard, switches nothing off."""
    meta, one, two = rig.meta, rig.one, rig.two
    one.table.add(Binding("pad:RP", "view.lines", "momentary", layer="preset"))
    two.table.add(Binding("pad:RP", "view.lines", "momentary", layer="preset"))
    one.reg["view.lines"].set(False)
    two.reg["view.lines"].set(True)
    io = _Pad()
    io.is_down = False
    pad = devices.PadDevice("pad", None, devices.Context(reg=one.reg, table=one.table), io=io)
    registry = devices.DeviceRegistry(devices=[pad])
    registry.point(meta.pointer, meta.panel_pointer)
    _pad_frame(registry, one, io, down=True)
    assert one.reg["view.lines"].value is True
    meta.point("pad", two)
    _pad_frame(registry, one, io, down=True)
    assert one.reg["view.lines"].value is False               # let go where it was held
    assert two.reg["view.lines"].value is True
    _pad_frame(registry, one, io, down=False)
    assert two.reg["view.lines"].value is True                # no press here, no release
    _pad_frame(registry, one, io, down=True)                  # the next press is this deck's
    assert two.reg["view.lines"].value is True
    _pad_frame(registry, one, io, down=False)
    assert two.reg["view.lines"].value is False


def test_a_controller_that_opens_later_gets_its_pointer():
    pointer = Pointer(SimpleNamespace(reg="r", table="t"))
    pad = devices.PadDevice("late", None, devices.Context(), io=None)
    pad.open = lambda: None
    pad.__dict__["status_"] = None
    registry = devices.DeviceRegistry(devices=[])
    registry.point(lambda role: pointer, Pointer(None))
    registry.devices.append(pad)
    assert pad.pointer is None
    assert registry._open(pad)
    assert pad.pointer is pointer and pad.reg == "r" and pad.table == "t"


def test_the_bridge_reads_through_its_pointer():
    b = bridge.Bridge.__new__(bridge.Bridge)
    b.reg = "first"
    assert b.reg == "first"
    b.point(Pointer(SimpleNamespace(reg="second")))
    assert b.reg == "second"


def test_the_mouse_on_deck_2_orbits_deck_2(rig, fake):
    meta, one, two = rig.meta, rig.one, rig.two
    g = app.glfw
    mouse = app.Mouse("render", one.reg, one.view, pointer=meta.pointer(MOUSE))
    assert mouse.yaw is one.reg["camera.yaw"]
    meta.point(MOUSE, two)
    before, was = _look(one), two.reg["camera.yaw"].base
    fake.cursor, fake.buttons = (100.0, 100.0), {g.MOUSE_BUTTON_LEFT}
    mouse.poll(shift=False)
    fake.cursor = (160.0, 100.0)
    mouse.poll(shift=False)
    assert mouse.yaw is two.reg["camera.yaw"] and mouse.view is two.view
    assert two.reg["camera.yaw"].base != was
    assert _look(one) == before


def test_the_keys_have_their_own_deck():
    """The frame's order is unchanged; the key rows are on the keys' deck,
    the pass stays on air."""
    log: list[str] = []
    h = _host(log)
    h.keys_pointer = Pointer(SimpleNamespace(router=Stub("keyed", log), reg=Stub("kreg", log)))
    assert app.frame(h, now=1.0, dt=1 / 60, fps=60.0) is True
    assert log == ["keyed.keys" if s == "router.keys" else s for s in ORDER]


# ---- nothing moved, in the app

def test_every_pointer_on_deck_1_lands_every_corpus_preset_as_before(tmp_path):
    """D1's walk over the corpus: with the holders pointed at deck 1 the state
    is the unpointed rig's, to the bit."""
    home = tmp_path / "home"
    plain = _walk(boot(home))
    r = boot(home)
    _pointed(r)
    undo.install(r.undo)
    _compare(_walk(r), plain, exact=True)


def test_main_points_every_holder_and_moves_none():
    src = inspect.getsource(app.main)
    for line in ("MetaController(deck, deck2, players, mix=mix)", "panel.pointer = library.pointer",
                 "device_reg.point(meta.pointer, meta.panel_pointer)", "pointer=meta.pointer(MOUSE)",
                 "on_air_pointer=meta.on_air_pointer", "panel_pointer=meta.panel_pointer",
                 "keys_pointer=meta.pointer(KEYS)", "on_air = meta.on_air",
                 "_draw_render(on_air.renderer, ctx, on_air.view,",
                 "for on in meta.decks", "meta.on_air.presets.current"):
        assert line in src, line
    for gone in ("_draw_render(renderer, ctx, s,", "presets.listeners.append(dream_check)"):
        assert gone not in src, gone
    assert ".point_panel(" not in src and "meta.point(" not in src
    (check,) = [n for n in ast.walk(ast.parse(src))
                if isinstance(n, ast.FunctionDef) and n.name == "dream_check"]
    assert "on.reg" in ast.unparse(check) and " reg[" not in ast.unparse(check)


def test_the_experiments_are_on_both_decks_over_one_state(rig):
    """The panel hook runs on the first deck only: what it registers that is no
    session group must reach the second, or a pad there loses it."""
    one, two = rig.one, rig.two
    state, swing = totem.TotemState(), poi.PoiState()
    totem.register(one.reg, state)
    poi.register(one.reg, swing, {})
    app._share_experiments(one.reg, two.reg, poi_cfg={})
    assert totem.state_of(two.reg) is state and poi.state_of(two.reg) is swing
    assert {p.id for p in one.reg} - {p.id for p in two.reg} == set()
    two.reg["totem.on"].set(True)
    assert state.on is True


def test_the_meta_controller_is_a_swap_target_of_a_watched_module(rig):
    from hyperspace import deck as deckmod
    from hyperspace import library as librarymod
    from hyperspace import players as playersmod
    from hyperspace import pointer as pointermod
    from hyperspace import undo as undomod

    rig.meta.pointer("a role")
    targets = rig.meta.targets()
    assert targets[0] == (rig.meta, "deck", "MetaController")
    assert {id(o) for o, *_ in targets} >= {id(p) for p in rig.meta.pointers.values()}
    assert "pointer" in MODULES and MODULES.index("pointer") < MODULES.index("seq_page")
    for obj, mod, cls in targets:
        assert mod in MODULES
        assert type(obj) is getattr({"deck": deckmod, "pointer": pointermod, "undo": undomod,
                                     "players": playersmod,
                                     "library": librarymod}[mod], cls)
