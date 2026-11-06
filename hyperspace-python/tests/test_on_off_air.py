"""Plan 44 D5d: the two `Deck`s as the owner sees them. HOLD, TAKE and DROP are gone
(the owner, 2026-11-04); two verbs remain, the crossfade and "copy on air to off air",
and the panel may look at either deck.

The absolute rule first: no patch reaches the other deck, by any road, either way
round. Then what `test_hold.py` promised, as promises of the new model; each names the
old test it replaces (DECISION-REGISTER row 697). Then the desk, the library verbs, the
frame's first line and the head.
"""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path
from types import SimpleNamespace as NS

import numpy as np
import pytest
from conftest import seed
from test_graph_legible import party as _party
from test_midi import cc, note, push
from test_pad_learn import ScriptedPad
from test_presets import put
from test_ui_shell import frame
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture
from test_undo import DT, boot

from hyperspace import (
    apc40,
    app,
    deck,
    gamepad,
    graph,
    graphview,
    hotreload,
    lfo,
    preset,
    routing,
    ui_graph,
    ui_media,
    undo,
)
from hyperspace.deck import Deck, Fade, MetaController, Mix
from hyperspace.learn import blocked
from hyperspace.library import PRESETS
from hyperspace.outputs import Preview, PreviewTextures, Switches, View, preview_size
from hyperspace.params import POSE_IDS, part_of
from hyperspace.routing import (
    CHASE_PARAM,
    Binding,
    Bindings,
    factory_desk,
    is_meta_row,
    led_shade,
    meta_refusal,
    meta_row_refusal,
)

CORPUS = Path(__file__).parent / "corpus" / "presets"
SIZE = (160, 100)
T = 7.0


def _doc(name: str) -> dict:
    return json.loads((CORPUS / f"{name}.json").read_text())


# ------------------------------------------------------------------- rigs

@pytest.fixture()
def rig(tmp_path):
    """`boot` plus deck 2, the desk and the library pointed as `app.main` points them,
    each deck on a look of its own."""
    r = boot(tmp_path / "home")
    two = Deck.beside(r.deck, lfos=lfo.LFOs(seed=1))
    meta = MetaController(r.deck, two, mix=r.mix)
    r.meta_undo = meta.undo
    r.lib.pointer = meta.panel_pointer
    r.midi.point(meta.pointer("apc40"), meta.panel_pointer)
    _looks(r.deck, two)
    yield NS(r=r, meta=meta, one=r.deck, two=two, lib=r.lib, mix=r.mix)
    undo.install(None)


def _looks(first, second) -> None:
    """Each deck on a look of its own, each undo stack quiet after it."""
    first.presets.load("party-acid")
    second.presets.load("party-trip")
    assert (first.presets.current, second.presets.current) == ("ACID", "TRIP")
    for d in (first, second):
        d.undo.tick(1.0)
        d.undo.tick(2.0)


def _gl(ctx, home, *, empty: bool = False):
    """Two decks with renderers on one context, as `app.main` builds them."""
    from hyperspace.render import Renderer

    seeded = boot(home)
    r1 = Renderer(ctx)
    r2 = r1.sibling()
    audio = NS(chain=seeded.chain, on=True)
    first = Deck.build(library=seeded.lib, control=seeded.control, audio=audio,
                       table=lambda reg: Bindings([]), renderer=r1,
                       attach=False, startup=False, install=False)
    second = Deck.beside(first, renderer=r2)
    mix = Mix()
    meta = MetaController(first, second, mix=mix)
    seeded.lib.pointer = meta.panel_pointer
    fade = Fade(first, second, mix, ctx, pointer=meta.on_air_pointer)
    if empty:
        first.presets.load("party-acid")
    else:
        _looks(first, second)
    return NS(r=seeded, lib=seeded.lib, meta=meta, one=first, two=second, fade=fade, mix=mix,
              decks=(first, second), chain=seeded.chain)


def _close(rig) -> None:
    rig.fade.close()
    for d in rig.decks:
        d.renderer.close()
    undo.install(None)


def _picture(ctx, d, t: float = T) -> np.ndarray:
    tex = ctx.texture(SIZE, 4)
    fbo = ctx.framebuffer([tex])
    fbo.use()
    ctx.viewport = (0, 0, *SIZE)
    v = View(Switches(), SIZE, target=fbo, viewport=(0, 0, *SIZE))
    d.renderer.draw_outputs(d.view, *SIZE, 1.0, [v], t_now=t)
    assert not v.error, v.error
    got = np.frombuffer(fbo.read(components=4), np.uint8).reshape(SIZE[1], SIZE[0], 4).copy()
    fbo.release()
    tex.release()
    return got


def _pass(rig) -> None:
    """Every deck's pass, on a clock that does not move, so only an edit moves a thing."""
    for d in rig.meta.decks:
        d.router.follow_macros()
    for d in rig.meta.decks:
        d.router.modulate(rig.chain, 0.0, T)
        d.reg.apply()


def _state(d) -> dict:
    """What a patch is, on one deck: nothing here may move when the other acts."""
    t = d.table
    return {"bases": d.reg.snapshot(part="patch"),
            "routes": [b.to_json() for b in t.routes()],
            "desk": [b.to_json() for b in t.desk()],
            "modifiers": t.modifiers_doc(d.reg),
            "macros": t.macros_doc(),
            "modgraph": d.router._modgraph_key(),
            "spec": d.presets.graph.spec,
            "name": d.presets.current,
            "turn": list(d.view.ang),
            "steps": [s.label for s in d.undo.stack]}


# ---------------------------------------------------- the leak test, both ways

def _route(rig, d):
    d.table.add(Binding("lane:0", "view.bright", "push", 0.2))


def _lfo_rate(rig, d):
    rig.lib.reg["lfo.1.rate"].set(3.5)                  # (the panel's handle)


def _modifier(rig, d):
    d.table.add_modifier("scale", ("lane:0",), d.reg, mul=0.5)


def _macro(rig, d):
    d.table.set_macros({"macro.1": {"label": "m", "subs": [
        {"base": "view.bright", "from": 0.1, "to": 0.9}]}}, d.reg)
    rig.lib.reg["macro.1"].set(0.3)


def _load(rig, d):
    rig.lib.load(PRESETS, "party-wake")


def _graph_edit(rig, d):
    e = graphview.Edit(graph=d.presets.graph, push=lambda label: undo.push(label, load=True))
    assert e.add_node("effect", "kaleido") is None


def _pattern_reset(rig, d):
    rig.lib.reset("pattern")


def _pattern_road(rig, d):
    p = next(p for p in d.reg if p.group == "pattern" and p.persist and part_of(p) == "patch"
             and getattr(p.kind, "value", "") == "continuous")
    p.set_norm(0.5 if p.norm != 0.5 else 0.25)


def _bright(rig, d):
    d.reg["view.bright"].set(0.17)
    d.undo.tick(3.0)
    d.undo.tick(4.0)


def _undo(rig, d):
    assert undo.here() is d.undo
    assert d.undo.undo()


def _save(rig, d):
    """A save over the name both decks have loaded, and the library's watch after it,
    with the panel on the other deck, which would land a file it saw change."""
    other = rig.meta.decks[0] if d is rig.meta.decks[1] else rig.meta.decks[1]
    d.reg["view.bright"].set(0.33)
    d.presets.save_as(d.presets.current)
    rig.meta.point_panel(other)
    rig.lib.poll(now=10_000.0)
    rig.meta.point_panel(d)


# road → (what it does, a set-up before the other deck is looked at)
ROADS = {"route": (_route, None), "lfo rate": (_lfo_rate, None), "modifier": (_modifier, None),
         "macro": (_macro, None), "load": (_load, None), "graph edit": (_graph_edit, None),
         "pattern strip reset": (_pattern_reset, _pattern_road), "undo": (_undo, _bright),
         "save": (_save, None)}


@pytest.mark.empty_frame
@pytest.mark.parametrize("who", [0, 1], ids=["deck 1 on air acts", "deck 2 off air acts"])
@pytest.mark.parametrize("road", list(ROADS))
def test_no_patch_reaches_the_other_deck(ctx, tmp_path, road, who):
    """The owner's absolute rule: whatever the panel does on its deck, by the road it
    really goes, the other's `snapshot`, `routes()`, modgraph key and GL frame are as
    they were to the bit. And each road does act on the deck it was on."""
    rig = _gl(ctx, tmp_path / "rig")
    d, other = rig.decks[who], rig.decks[1 - who]
    act, ready = ROADS[road]
    if road == "save":                     # the same name on both: the file is shared
        other.presets.load(d.presets.current)
    rig.meta.point_panel(d)
    if ready is not None:
        ready(rig, d)
    _pass(rig)
    theirs, pic = _state(other), _picture(ctx, other)
    assert (_picture(ctx, other) == pic).all(), "the frame is not repeatable: no proof"
    mine = _state(d)
    act(rig, d)
    _pass(rig)
    assert _state(d) != mine or road == "save", "the road did nothing to prove"
    now = _state(other)
    assert {k: (theirs[k], now[k]) for k in theirs if theirs[k] != now[k]} == {}
    assert (_picture(ctx, other) == pic).all()
    assert ctx.error == "GL_NO_ERROR"
    _close(rig)


def test_a_pad_press_on_the_off_air_deck_reaches_only_it(rig):
    """A library verb by the row road, the one a panel road cannot show."""
    rig.meta.register("apc40", 2)
    rig.meta.move_player(2, "off_air")
    theirs = _state(rig.one)
    rig.two.presets.lib.project.bank[0] = "party-wake"
    rig.two.reg["preset.select"].set(0)
    assert rig.two.presets.current == "WAKE"
    assert _state(rig.one) == theirs


# --------------------------------------------------- what test_hold promised, rewritten

@pytest.mark.empty_frame
def test_on_gl_on_air_keeps_its_frame_while_the_other_deck_is_edited(ctx, tmp_path):
    """Was `..._the_projector_keeps_the_held_frame_while_the_preview_shows_the_edit`:
    a new preset and a turned knob on the deck off air, and on air is the same bytes;
    the fader across, the outputs show the edit."""
    rig = _gl(ctx, tmp_path / "rig")
    rig.meta.point_panel(rig.two)
    before = _picture(ctx, rig.one)
    assert before[..., :3].max() > 0
    rig.two.presets.load("party-wake")
    rig.two.reg["view.bright"].set(0.2)
    assert (_picture(ctx, rig.one) == before).all()
    edited = _picture(ctx, rig.two)
    assert not (edited == before).all()
    rig.mix.xfade = 1.0
    rig.meta.tick(T, DT)
    assert rig.meta.on_air is rig.two and rig.fade.k == 0.0
    assert (_picture(ctx, rig.meta.on_air) == edited).all()
    _close(rig)


@pytest.mark.empty_frame
def test_on_gl_a_bus_cable_cut_off_air_stays_off_the_picture_on_air(ctx, tmp_path):
    """Was `..._a_bus_cable_cut_after_the_hold_stays_off_the_projector`: the cuts are
    the preset's (plan 44 D3), so each deck's renderer reads its own."""
    rig = _gl(ctx, tmp_path / "rig")
    rig.two.presets.load("party-acid")
    before = _picture(ctx, rig.one)
    assert (_picture(ctx, rig.two) == before).all()
    rig.two.presets.bus = rig.two.presets.bus.cutting(graph.bus_wire(1, "image"))
    assert rig.two.renderer.bus_source is rig.two.presets
    assert _picture(ctx, rig.two)[..., :3].max() == 0
    assert (_picture(ctx, rig.one) == before).all()
    _close(rig)


@pytest.mark.empty_frame
def test_on_gl_a_graph_edit_off_air_leaves_the_wiring_on_air(ctx, tmp_path):
    """Was `..._the_program_draws_the_held_wiring_while_a_graph_edit_lands`."""
    rig = _gl(ctx, tmp_path / "rig")
    rig.meta.point_panel(rig.two)
    wiring, built = rig.one.renderer.wiring, _picture(ctx, rig.one)
    e = graphview.Edit(graph=rig.two.presets.graph, push=lambda s: undo.push(s, load=True))
    assert e.add_node("effect", "kaleido") is None
    _picture(ctx, rig.two)
    assert rig.one.renderer.wiring is wiring
    assert (_picture(ctx, rig.one) == built).all()
    _close(rig)


@pytest.mark.empty_frame
def test_on_gl_a_blank_graph_off_air_leaves_on_air_whole_and_a_fade_into_it_is_black(ctx, tmp_path):
    """Was `..._a_blank_graph_landed_while_held_leaves_the_projector_whole`. And the
    owner, 2026-11-04: a crossfade may fade into an empty deck, which is black."""
    rig = _gl(ctx, tmp_path / "rig", empty=True)
    assert rig.two.presets.current is None and rig.two.presets.graph.spec is None
    before = _picture(ctx, rig.one)
    assert before[..., :3].max() > 0
    assert _picture(ctx, rig.two)[..., :3].max() == 0
    rig.mix.xfade = 1.0
    rig.meta.tick(T, DT)
    assert rig.meta.on_air is rig.two
    assert _picture(ctx, rig.meta.on_air)[..., :3].max() == 0
    _close(rig)


def test_a_bus_cut_off_air_is_on_that_deck_and_its_undo_puts_it_back(rig):
    """Was `test_a_bus_cable_cut_after_the_hold...` and `test_drop_puts_a_bus_cable_cut...`,
    headless: one step on the deck it was cut on, the other deck's cuts as they were."""
    rig.meta.point_panel(rig.two)
    cuts = rig.one.presets.bus
    undo.push("cut", load=True)
    rig.two.presets.bus = rig.two.presets.bus.cutting(graph.bus_wire(1, "image"))
    assert rig.one.presets.bus is cuts
    assert graph.bus_wire(1, "image") in rig.two.presets.bus.cut
    assert undo.here().undo()
    assert graph.bus_wire(1, "image") not in rig.two.presets.bus.cut


def test_edits_off_air_come_back_one_step_at_a_time_and_on_air_never_moves(rig):
    """Was `test_drop_goes_back_to_the_hold_point_as_one_undo_step`: there is no Drop,
    so ⌘Z on the deck the panel is on is how an edit goes back."""
    rig.meta.point_panel(rig.two)
    theirs = _state(rig.one)
    was = rig.two.reg["view.bright"].base
    rig.two.reg["view.bright"].set(0.21)
    rig.two.undo.tick(3.0)
    rig.two.undo.tick(4.0)
    assert len(rig.two.undo.stack) >= 1 and undo.here() is rig.two.undo
    assert undo.here().undo()
    assert rig.two.reg["view.bright"].base == pytest.approx(was)
    assert _state(rig.one) == theirs


def test_a_whole_new_look_off_air_is_one_step_back_and_one_forward(rig):
    """Was `test_drop_after_a_whole_new_look_is_one_undo_step_back_and_one_forward`."""
    rig.meta.point_panel(rig.two)
    was, n = _state(rig.two)["bases"], len(rig.two.undo.stack)
    rig.lib.load(PRESETS, "party-wake")
    assert rig.two.presets.current == "WAKE" and len(rig.two.undo.stack) == n + 1
    assert undo.here().undo()
    assert rig.two.presets.current == "TRIP" and _state(rig.two)["bases"] == was
    assert undo.here().redo()
    assert rig.two.presets.current == "WAKE"
    assert rig.one.presets.current == "ACID"


def test_a_load_resets_the_delays_of_its_own_deck_only(rig):
    """Was `test_a_load_while_held_resets_the_previews_delays_and_the_projectors_at_take`."""
    reset = []
    for d, name in ((rig.one, "one"), (rig.two, "two")):
        d.presets.graph.attach(NS(wiring=None, ghost_states={}, name=name,
                                  reset_delays=lambda name=name: reset.append(name)))
    rig.two.presets.load("party-wake")
    assert reset == ["two"]


def test_a_load_off_air_keeps_the_eye_and_turn_on_air_and_brings_its_own(rig):
    """Was `test_a_preset_loaded_under_hold_keeps_the_projectors_eye_and_turn_until_take`.
    Each deck has its own view, so nothing waits: the deck it landed on has its pose."""
    rig.meta.point_panel(rig.two)
    one = rig.one
    fov, turn = one.reg["eye.fov"].base, list(one.view.ang)
    doc = _doc("dial")
    doc["values"]["eye.fov"] = 70.0
    pose = [0.1, -0.2, 0.3, 0.4, -0.5, 0.6]
    doc[preset.POSE_KEY] = dict(zip(POSE_IDS, pose, strict=True))
    rig.two.presets.load_doc(doc)
    assert rig.two.view.ang == pose and rig.two.reg["eye.fov"].base == 70.0
    assert one.view.ang == turn and one.reg["eye.fov"].base == fov
    saved = rig.two.presets.document("x")[preset.POSE_KEY]
    assert [saved[k] for k in POSE_IDS] == pose


def test_the_output_controls(rig):
    """Was `test_the_output_controls`: the crossfader and its seconds, the meta
    controller's, both decks' one param; hold, take and drop are gone."""
    reg = rig.one.reg
    for pid in ("output.xfade", "output.xfade_s"):
        p = reg[pid]
        assert p is rig.two.reg[pid] and part_of(p) == "shared_meta"
        assert p.group == "output" and not p.persist and not p.modulatable
    for pid in ("output.hold", "output.take", "output.drop"):
        assert pid not in reg
    assert not hasattr(rig.one, "hold") and not hasattr(rig.one.presets.graph, "hold")
    assert not hasattr(reg, "chase_guard")
    assert not (Path(deck.__file__).parent / "hold.py").exists()
    assert "hold" not in hotreload.MODULES


def test_the_two_verbs_on_the_rows_of_the_desk(tmp_path):
    """Was `test_learned_desk_buttons_light_while_held`: what the desk has now is its
    crossfader and its MASTER, the factory's rows over fake ports, each moving the
    meta controller's param whichever deck the desk's player is on."""
    r = boot(tmp_path / "home")
    two = Deck.beside(r.deck, lfos=lfo.LFOs(seed=1))
    meta = MetaController(r.deck, two, mix=r.mix)
    r.midi.point(meta.pointer("apc40"), meta.panel_pointer)
    r.mix.xfade = 0.0
    for on_air in (True, False):
        r.mix.xfade = 0.0
        if not on_air:
            meta.register("apc40", 2)
            meta.move_player(2, "off_air")
        assert (r.midi.reg is r.reg) is on_air
        xf, dim = r.reg["output.xfade"], r.reg["output.dim"]
        rows = {b.target: b for b in r.midi.table.bindings}
        rows["output.xfade"].caught = rows["output.dim"].caught = False
        push(r, cc(apc40.CC_XFADE, 0), cc(apc40.CC_XFADE, 64))
        assert xf.value == pytest.approx(64 / 127, abs=0.01), on_air
        push(r, cc(apc40.CC_MASTER, 127), cc(apc40.CC_MASTER, 64))
        assert dim.value == pytest.approx(64 / 127, abs=0.02), on_air
    undo.install(None)


def test_preview_size_keeps_the_aspect_under_both_caps():
    """Kept from `test_hold`: the deck off air's backdrop still draws at it."""
    assert preview_size((1920, 1080), None) == (1280, 720)
    assert preview_size((1920, 1080), (960, 540)) == (960, 540)
    assert preview_size((640, 360), None) == (640, 360)


def test_the_head_and_the_title_say_which_deck_the_panel_is_on(rig):
    """Was `test_the_head_line_says_how_long_and_what_changed`. DQ7."""
    meta = rig.meta
    assert meta.words(rig.one) == "deck 1 · on air" and meta.words(rig.two) == "deck 2 · off air"
    assert app.control_title(meta).endswith("controls · deck 1 · on air")
    panel = NS(meta=meta)
    assert not ui_graph.panel_off_air(panel) and not ui_graph.panel_off_air(NS())
    meta.point_panel(rig.two)
    assert ui_graph.panel_off_air(panel)
    assert app.control_title(meta).endswith("controls · deck 2 · off air")
    rig.mix.xfade = 1.0
    meta.tick(T, DT)
    assert meta.words(rig.two) == "deck 2 · on air" and not ui_graph.panel_off_air(panel)
    assert meta.words(rig.one) == "deck 1 · off air"


def _draws(monkeypatch, log, size=None):
    from test_app_boundary import _Ctx, _rig_slots, _SwapGlfw

    monkeypatch.setattr(app, "glfw", _SwapGlfw(log, {"w1": size} if size else None or {}))
    monkeypatch.setattr(app, "_samples_of", lambda ctx, target: None)     # (no GL here)
    return _Ctx(log), _rig_slots("x")


class _Tap:
    tex = "tap-tex"

    def fit(self, size):
        return "fbo"


def _fade_stub(log, off):
    return NS(off_air=off, k=0.0, warm_deck=None, begin_frame=lambda: None,
              warm=lambda *a: False, draw=lambda *a: False,
              preview=lambda pv, *a: (log.append("preview"), pv.publish("deck-tex", 0.0), True)[-1])


def test_off_air_the_outputs_draw_on_air_and_the_backdrop_is_the_panels_deck(monkeypatch):
    """Was `test_held_the_outputs_draw_the_program_and_the_preview_follows`: every output
    from the on-air renderer, output 1 riding the inset (`monitor`), the page's backdrop
    the deck off air's own picture, one flush."""
    log: list[str] = []
    ctx, slots = _draws(monkeypatch, log, (1600, 1000))
    calls = []
    main = NS(bg_alpha=1.0, max_frame=None,
              draw_outputs=lambda s, w, h, dpr, views, t_now=None: calls.append(views))
    off = object()
    preview, monitor = Preview(), Preview()
    preview.tap, monitor.tap = _Tap(), object()
    preview.want()
    monitor.want()
    app._draw_render(main, ctx, object(), slots, flush=lambda: log.append("flush"),
                     preview=preview, monitor=monitor, fade=_fade_stub(log, off), panel_deck=off)
    assert len(calls) == 1 and calls[0][0].publish == [monitor]
    assert calls[0][0].tap is monitor.tap
    assert "preview" in log and preview.tex == "deck-tex"
    assert not preview.wanted and not monitor.wanted and log.count("flush") == 1


def test_with_the_page_closed_the_deck_off_air_draws_nothing(monkeypatch):
    """Was `test_held_with_the_page_closed_draws_no_preview`."""
    log: list[str] = []
    ctx, slots = _draws(monkeypatch, log)
    off = object()
    main = NS(bg_alpha=1.0, draw_outputs=lambda *a, **k: log.append("draw"))
    app._draw_render(main, ctx, object(), slots, flush=lambda: log.append("flush"),
                     preview=Preview(), monitor=Preview(), fade=_fade_stub(log, off), panel_deck=off)
    assert log.count("draw") == 1 and "preview" not in log and "flush" not in log


def test_on_the_on_air_deck_the_backdrop_is_output_1_and_no_inset(monkeypatch):
    log: list[str] = []
    ctx, slots = _draws(monkeypatch, log)
    calls = []
    on, off = object(), object()
    main = NS(bg_alpha=1.0, draw_outputs=lambda s, w, h, dpr, views, t_now=None: calls.append(views))
    preview, monitor = Preview(), Preview()
    preview.tap = object()
    preview.want()
    monitor.want()
    app._draw_render(main, ctx, object(), slots, flush=lambda: None, preview=preview,
                     monitor=monitor, fade=_fade_stub(log, off), panel_deck=on)
    assert calls[0][0].publish == [preview] and monitor.wanted


@pytest.mark.empty_frame
def test_the_on_air_inset_and_red_frame_draw_only_off_air(shell_rig):  # noqa: F811
    """Was `test_the_projector_inset_draws_framed_while_held`."""
    from imgui_bundle import imgui

    asked = []
    mon = NS(tex=NS(glo=7, size=(160, 90)), want=lambda: asked.append(True))
    one, two = object(), object()
    panel = NS(meta=NS(panel=two, on_air=one), monitor=mon)
    imgui.new_frame()
    imgui.begin("probe")
    try:
        dl = imgui.get_window_draw_list()
        before = dl.vtx_buffer.size()
        ui_graph._monitor(NS(meta=NS(panel=one, on_air=one), monitor=mon), (0.0, 0.0), (800.0, 600.0))
        assert not asked and dl.vtx_buffer.size() == before
        ui_graph._monitor(panel, (0.0, 0.0), (800.0, 600.0))
        assert asked == [True] and dl.vtx_buffer.size() > before
    finally:
        imgui.end()
        imgui.end_frame()


def test_the_frame_is_under_a_popup_and_out_of_panel_graph(shell_rig, monkeypatch):  # noqa: F811
    """On the page's list, so a popup lies over it, and among what `replay` cuts out."""
    r = shell_rig
    frame(r.panel, "graph")
    frame(r.panel, "graph")
    on = r.panel.canvas_px[4]
    monkeypatch.setattr(ui_graph, "panel_off_air", lambda panel: True)
    frame(r.panel, "graph")
    frame(r.panel, "graph")
    off = r.panel.canvas_px[4]
    assert off[1] - off[0] > on[1] - on[0]         # the frame's indices, cut out too


def _on_party(rig):
    seed(rig.lib.home, "presets")
    return _party(rig)


def test_the_page_wants_its_thumbnails_from_the_panels_deck(shell_rig):  # noqa: F811
    """Was `test_held_the_page_wants_from_the_previews_thumbnails`: each deck's own
    `PreviewTextures`, whichever is on air."""
    r = shell_rig
    st = _on_party(r)
    g = r.panel.renderer._graph
    mine, theirs = PreviewTextures(None), PreviewTextures(None)
    r.panel.renderer = NS(_graph=g, thumbs=mine, stats={})
    r.panel.preview, r.panel.monitor = Preview(), Preview()
    st["preset_only"], st["pan"] = False, (-1600.0, 0.0)
    frame(r.panel, "graph")
    frame(r.panel, "graph")
    got = ui_graph._state(r.panel)
    assert got["thumbs"] is mine and got["preview"] is r.panel.preview
    assert mine.wanted and not theirs.wanted


@pytest.mark.empty_frame
def test_on_gl_each_deck_makes_its_own_thumbnails(ctx, tmp_path):
    """Was `..._held_the_preview_renderer_makes_the_thumbnails_and_the_main_none`, and
    `..._a_hold_with_the_page_closed_makes_no_thumbnail`: only a renderer the page
    asked of makes any; the deck off air's are its own."""
    rig = _gl(ctx, tmp_path / "rig")
    one, two = rig.one.renderer, rig.two.renderer
    _picture(ctx, rig.two)                         # page closed: nothing asked
    assert two.thumbs.count == 0 and not two.thumbs.tex
    assert two.thumbs is not one.thumbs
    panel = NS(renderer=two, preview=Preview())
    th, _, _ = ui_graph.picture_sources(panel)
    assert th is two.thumbs
    th.want({"scene": "picture"})
    _picture(ctx, rig.two)
    assert two.thumbs.count == 1 and "scene" in two.thumbs.tex and one.thumbs.count == 0
    _close(rig)


# ------------------------------------------------------- the reserved desk controls

@pytest.mark.parametrize("control", apc40.META_CONTROLS)
def test_no_preset_may_learn_or_bind_the_reserved_controls(rig, control):
    """The owner: the APC "inherits our generic controller setup ... and it should have
    extensions". Refused whatever the table holds on it, so a deleted row frees nothing."""
    table = rig.two.table
    assert blocked(table, control) == "invariant"
    table.meta_table.set_rows([b for b in table.meta_table.rows if b.source != control])
    assert not any(b.source == control for b in table.bindings)
    assert blocked(table, control) == "invariant"
    notes = table.set_desk([Binding(control, "view.bright", "abs")])
    assert any("invariant" in n for n in notes)
    assert not any(b.source == control for b in table.desk())


def test_only_the_first_desk_of_the_apc_profile_is_reserved():
    """Another desk's CC 14 and 15 are its own, as SHIFT's note is."""
    t = Bindings.factory("apc40")
    t.midi_roles = ("apc40", "launch")
    for source in (f"cc@launch:0:{apc40.CC_XFADE}", f"cc@launch:0:{apc40.CC_MASTER}"):
        assert not t.is_invariant(Binding(source, "x", "abs", layer="preset")), source
        assert blocked(t, source) is None
    assert t.is_invariant(Binding(f"cc@apc40:0:{apc40.CC_XFADE}", "x", "abs", layer="preset"))
    other = Bindings([], profile="launchpad")
    assert not other.is_invariant(Binding(f"cc:0:{apc40.CC_XFADE}", "x", "abs", layer="preset"))


def test_a_generic_desks_rows_on_those_numbers_are_not_moved():
    rows = [Binding(f"cc:0:{apc40.CC_MASTER}", "master.gain", "abs"),
            Binding(f"cc:0:{apc40.CC_XFADE}", "output.dim", "abs")]
    got, _notes = routing.remap_factory(rows, "launchpad")
    assert [(b.source, b.target) for b in got[:2]] == [(b.source, b.target) for b in rows]


def test_a_deleted_reserved_row_comes_back_at_the_next_load_and_a_changed_one_stays():
    table = Bindings.factory("apc40")
    gone = f"cc:0:{apc40.CC_XFADE}"
    rows = [b for b in table.bindings if b.is_midi and b.source != gone]
    got, notes = routing.remap_factory(rows)
    (row,) = [b for b in got if b.source == gone]
    assert row.target == "output.xfade" and row.ring == 0 and row.pickup
    assert any(gone in n and "reserved" in n for n in notes)
    assert routing.remap_factory(got)[1] == []
    mine = [Binding(gone, "view.bright", "abs"), *rows]
    assert [b.target for b in routing.remap_factory(mine)[0] if b.source == gone] == ["view.bright"]


@pytest.mark.parametrize(("x", "k"), [(0.0, 0.0), (1 / 127, 0.0), (0.002, 0.0), (2 / 127, 0.0),
                                      (0.5, 0.5), (1.0, 1.0), (126 / 127, 1.0)])
def test_a_fader_a_step_off_its_end_is_at_its_end(rig, x, k):
    """A worn fader at CC 1: it mixes nothing in, and bars nothing."""
    from hyperspace.deck import between_ends

    fade = Fade(rig.one, rig.two, rig.mix, pointer=rig.meta.on_air_pointer)
    rig.mix.xfade = x
    assert fade.k == pytest.approx(k)
    assert between_ends(x) == (k == 0.5)
    if k == 0.0:
        assert rig.meta.bars_load() is None and rig.meta.bars_copy() is None


def _timed_rig(tmp_path):
    r = boot(tmp_path / "home")
    two = Deck.beside(r.deck, lfos=lfo.LFOs(seed=1))
    meta = MetaController(r.deck, two, mix=r.mix)
    r.midi.point(meta.pointer("apc40"), meta.panel_pointer)
    r.reg["output.xfade_s"].set(30.0)
    meta.crossfade()
    meta.tick(0.0, DT)
    meta.tick(10.0, DT)
    assert r.mix.xfade == pytest.approx(1 / 3, abs=0.01)
    r.midi.poll()                                      # the moved value uncatches the fader
    return r, meta


def test_a_hand_on_the_desks_fader_ends_a_timed_fade_far_from_its_value(tmp_path):
    """Soft pickup alone would ignore it until it crossed the moving value."""
    r, meta = _timed_rig(tmp_path)
    xf = r.reg["output.xfade"]
    at = xf.value
    (row,) = [b for b in r.midi.table.bindings if b.target == "output.xfade"]
    assert not row.caught
    push(r, cc(apc40.CC_XFADE, 110), cc(apc40.CC_XFADE, 113))    # far above the value
    assert meta.timed is None and xf.value == pytest.approx(at)
    meta.tick(20.0, DT)
    assert xf.value == pytest.approx(at)                         # ended where it was
    push(r, cc(apc40.CC_XFADE, 30))                              # across it: caught
    assert row.caught
    undo.install(None)


def test_a_pot_jittering_at_rest_leaves_a_timed_fade_running(tmp_path):
    r, meta = _timed_rig(tmp_path)
    for v in (0, 1, 0, 2, 1, 2, 0):
        push(r, cc(apc40.CC_XFADE, v + 110))
    assert meta.timed is not None
    meta.tick(40.0, DT)
    assert r.mix.xfade == 1.0
    undo.install(None)


@pytest.mark.parametrize("how", ["between the ends", "in a timed fade"])
def test_copy_is_refused_while_the_deck_off_air_is_in_the_picture(rig, how):
    said = []
    panel = NS(meta=rig.meta, library=NS(say=lambda status=None, *, warning=None: said.append(warning)))
    if how == "between the ends":
        rig.mix.xfade = 0.4
    else:
        rig.meta.crossfade()
    theirs = _state(rig.two)
    ui_graph.copy_on_air(panel)
    assert _state(rig.two) == theirs and "not copied" in said[0]


def test_a_copy_that_will_not_land_is_said_and_leaves_no_step(rig, monkeypatch):
    said = []
    panel = NS(meta=rig.meta, library=NS(say=lambda status=None, *, warning=None: said.append(warning)))
    n = len(rig.two.undo.stack)

    def refuse(doc):
        raise ValueError("a value would not land")

    monkeypatch.setattr(rig.two.presets, "load_doc", refuse)
    ui_graph.copy_on_air(panel)                       # no raise out of the panel's draw
    assert "not copied" in said[0] and "would not land" in said[0]
    rig.two.undo.tick(10.0)
    rig.two.undo.tick(20.0)
    assert len(rig.two.undo.stack) == n


def test_the_sheet_says_what_the_keys_do():
    from hyperspace.ui import CHEATSHEET

    words = dict(row for row in CHEATSHEET if isinstance(row, tuple) and len(row) == 2)
    assert "off air" in words["F1–F8"] and "off air" in words["Home"]
    assert not any("refused" in w for w in words.values())


def test_the_crossfader_keeps_its_catch_and_a_timed_fade_is_not_undoable(rig):
    meta = rig.meta
    n = len(rig.one.undo.stack), len(meta.undo.stack)
    rig.one.reg["output.xfade_s"].set(0.0)
    meta.crossfade()
    meta.tick(T, DT)
    for k in range(3):
        for s in meta.stacks:
            s.tick(T + k)
    assert meta.on_air is rig.two
    assert (len(rig.one.undo.stack), len(meta.undo.stack)) == n


# ----------------------------------------------------------------- the library verbs

VERBS = ["preset.select", "preset.next", "preset.prev", "preset.load.0",
         "preset.list.next", "preset.list.prev", "preset.home"]


def _press(reg, verb, k=0):
    if verb == "preset.select":
        reg[verb].set(k)
    else:
        reg[verb].fire()


def _bank(rig, *names):
    project = rig.one.presets.lib.project
    project.bank[:] = [None] * len(project.bank)
    for k, name in enumerate(names):
        project.bank[k] = name
    project.startup = names[0]
    return project


def _quiet(d):
    d.undo.tick(50.0)
    d.undo.tick(51.0)


@pytest.mark.parametrize("verb", VERBS)
def test_a_library_verb_from_either_deck_loads_off_air_and_the_room_is_as_it_was(rig, verb):
    """The owner, 2026-11-06, row 700: a press "always loads into the off-air Deck, never
    touching the room". Whichever deck's param was pressed; nothing on air moves, its
    undo stack included; the off-air stack has the step; the status line says so."""
    _bank(rig, "party-wake", "party-tumble")
    for pressed in (rig.one, rig.two):
        rig.two.presets.load("party-trip")
        _quiet(rig.two)
        theirs, steps = _state(rig.one), len(rig.two.undo.stack)
        rig.lib.status = ""
        _press(pressed.reg, verb)
        _quiet(rig.two)
        assert rig.two.presets.current != "TRIP"
        assert _state(rig.one) == theirs
        assert len(rig.two.undo.stack) == steps + 1
        assert rig.lib.status == (f"{rig.two.presets.current} loaded off air on deck 2; "
                                  "the room still sees deck 1")


def test_the_strip_reads_the_panels_deck_whichever_deck_a_press_loaded(rig):
    _bank(rig, "party-wake")
    strip = rig.lib.current(PRESETS)
    rig.one.reg["preset.load.0"].fire()
    assert rig.lib.current(PRESETS) == strip, "the panel is on deck 1"
    rig.meta.point_panel(rig.two)
    assert rig.lib.current(PRESETS) != strip
    assert rig.lib.current(PRESETS) == rig.two.presets.lib.current(PRESETS)


def test_next_and_prev_step_from_what_the_deck_off_air_holds(rig):
    project = _bank(rig, "party-wake", "party-tumble", "party-acid")
    rig.one.reg["preset.load.2"].fire()              # (off air: ACID, slot 2)
    assert rig.two.presets.current == "ACID"
    rig.one.presets.active_slot = 1                  # on air on slot 1: not what is read
    rig.one.reg["preset.next"].fire()
    assert rig.two.presets.current == "WAKE", "it wraps from slot 2 to slot 0"
    assert rig.two.presets.active_slot == 0 and project.active == 1
    rig.one.reg["preset.prev"].fire()
    assert rig.two.presets.current == "ACID"
    listing = rig.lib.list(PRESETS)
    held = rig.two.presets.lib.current(PRESETS)
    rig.one.reg["preset.list.next"].fire()
    assert rig.two.presets.lib.current(PRESETS) == listing[(listing.index(held) + 1) % len(listing)]


def test_the_landing_follows_the_crossfader(rig):
    """On air went across, so deck 1 is off air: it takes the press, whichever is pressed."""
    _bank(rig, "party-wake", "party-tumble")
    rig.mix.xfade = 1.0
    rig.meta.tick(T, DT)
    assert rig.meta.on_air is rig.two
    theirs = _state(rig.two)
    rig.two.reg["preset.select"].set(0)
    assert rig.one.presets.current == "WAKE" and _state(rig.two) == theirs
    rig.one.reg["preset.select"].set(1)
    assert rig.one.presets.current == "TUMBLE" and _state(rig.two) == theirs
    assert "on deck 1; the room still sees deck 2" in rig.lib.status


@pytest.mark.parametrize("verb", VERBS)
@pytest.mark.parametrize("who", [0, 1], ids=["pressed on air", "pressed off air"])
def test_between_the_ends_both_decks_are_on_air_and_a_press_is_refused(rig, verb, who):
    _bank(rig, "party-wake", "party-tumble")
    rig.mix.xfade = 0.3
    states = _state(rig.one), _state(rig.two)
    rig.lib.warning = ""
    _press((rig.one, rig.two)[who].reg, verb)
    assert (_state(rig.one), _state(rig.two)) == states
    assert "between its ends" in rig.lib.warning and "not loaded" in rig.lib.warning


def test_a_pad_is_refused_from_the_first_frame_of_a_timed_fade(rig):
    """Still within `ENDS` the deck off air is about to come up: a load there would
    be a look changed from the desk, in front of the room."""
    _bank(rig, "party-wake")
    rig.one.reg["output.xfade_s"].set(30.0)
    rig.meta.crossfade()
    was = rig.two.presets.current
    for t in (0.0, 0.1):                               # asked for; then running, inside ENDS
        rig.meta.tick(t, DT)
        assert rig.mix.xfade < deck.ENDS and rig.meta.timed is not None
        for d in (rig.one, rig.two):
            rig.lib.warning = ""
            d.reg["preset.select"].set(0)
            assert rig.two.presets.current == was and "not loaded" in rig.lib.warning
    rig.meta.tick(100.0, DT)
    assert rig.meta.timed is None and rig.meta.bars_load() is None      # it arrived


def _clip(k):
    n, ch = apc40.BANK_PADS[k]
    return n, ch


def test_the_apc_on_air_loads_off_air_by_a_real_press_and_lights_that(rig):
    """The default the owner met: player 1, on air. A pad works, QUANT and OVERDUB too,
    and the pads are lit for the deck a press lands on, on the wire as on the panel's desk."""
    _bank(rig, "party-wake", "party-tumble")
    assert rig.meta.pointer("apc40").deck is rig.one
    theirs = _state(rig.one)
    n, ch = _clip(1)
    push(rig.r, note(n, channel=ch), note(n, 0, channel=ch))
    assert rig.two.presets.current == "TUMBLE" and _state(rig.one) == theirs
    pads = {int(b.value): b for b in rig.one.table.active() if b.target == "preset.select"}
    reg = rig.one.reg
    assert led_shade(pads[1], reg["preset.select"]) == "on"
    assert led_shade(pads[0], reg["preset.select"]) == "held"
    sent = [m for m in rig.r.out.sent if m.type == "note_on" and m.note == n and m.channel == ch]
    assert sent[-1].velocity == apc40.GREEN
    push(rig.r, note(apc40.N_QUANT), note(apc40.N_QUANT, 0))
    assert rig.two.presets.current == "WAKE" and _state(rig.one) == theirs
    assert led_shade(pads[0], reg["preset.select"]) == "on"
    rig.two.presets.load("party-trip")
    push(rig.r, note(apc40.N_OVERDUB), note(apc40.N_OVERDUB, 0))
    assert rig.two.presets.current == "WAKE" and _state(rig.one) == theirs


def test_the_pads_light_says_the_deck_off_air_from_both_decks_and_follows_the_fader(rig):
    _bank(rig, "party-wake", "party-tumble")
    rig.two.reg["preset.select"].set(0)
    rig.one.presets.lib.project.active = 1
    for d in (rig.one, rig.two):
        assert d.reg["preset.select"].value == 0, "the slot off air, whoever reads it"
    rig.mix.xfade = 1.0
    rig.meta.tick(T, DT)
    for d in (rig.one, rig.two):
        assert d.reg["preset.select"].value == 1


def test_f_keys_and_home_load_off_air(rig):
    """The keys sit on the picture, and go the same road (row 700's second question)."""
    import glfw

    _bank(rig, "party-wake", "party-tumble")
    theirs = _state(rig.one)

    rig.r.router.keys(NS(pressed=lambda code: code == glfw.KEY_F2))
    assert rig.two.presets.current == "TUMBLE"
    rig.r.router.keys(NS(pressed=lambda code: code == glfw.KEY_HOME))
    assert rig.two.presets.current == "WAKE"
    assert _state(rig.one) == theirs


def test_a_held_empty_pad_on_air_still_saves_there_and_blinks(rig):
    """A save is not changed, and its pad's light is about the other deck, so the
    blink that confirms it does not wait for the light to change."""
    from hyperspace import midi

    project = rig.one.presets.lib.project
    empty = project.next_empty()
    n, ch = _clip(empty)
    t = [0.0]
    rig.r.midi.clock = lambda: t[0]
    theirs = _state(rig.two)
    push(rig.r, note(n, channel=ch))
    t[0] = midi.HOLD_S + 0.01
    rig.r.midi.poll()
    assert project.bank[empty] is not None and rig.one.presets.active_slot == empty
    assert _state(rig.two) == theirs
    assert rig.r.midi._hold_state()[1], "the pad blinks"


def test_an_empty_pad_says_how_to_fill_it_and_a_hold_still_saves_on_air(rig):
    d = rig.one
    project = d.presets.lib.project
    empty = project.next_empty()
    rig.lib.warning = ""
    d.reg["preset.select"].set(empty)
    assert "an empty slot" in rig.lib.warning
    was = d.presets.current
    assert d.reg["preset.select"].held(empty)
    assert project.bank[empty] is not None and d.presets.current != was
    assert rig.two.presets.current == "TRIP"


def test_the_panels_own_load_on_air_is_the_intentional_one(rig):
    rig.lib.load(PRESETS, "party-wake")
    assert rig.one.presets.current == "WAKE"
    assert rig.two.presets.current == "TRIP"
    rig.meta.point_panel(rig.two)
    rig.lib.load(PRESETS, "party-tumble")
    assert rig.two.presets.current == "TUMBLE" and rig.one.presets.current == "WAKE"


def _library_verb(pid):
    """`preset.*`: the whole group is refused now (row 746), which replaced row 752's list."""
    return pid.startswith("preset.")


# ------------------------------------------- no patch's row can press any `preset.*` (row 746)

CARRIED = ["preset.select", "preset.next", "preset.prev", "preset.home", "preset.load.0",
           "preset.list.next", "preset.list.prev"]


@pytest.mark.parametrize("verb", CARRIED)
def test_a_preset_cannot_carry_a_row_on_a_library_verb_by_any_door(verb):
    """The absolute rule: from a row a verb lands on the other deck, so a row a preset
    carries would be one patch changing another. Refused in words at each door."""
    t = Bindings()
    for row in (Binding("note:0:60", verb, "toggle", layer="preset"),
                Binding("seq:0", verb, "push", 1.0), Binding("lfo:0", verb, "position", 1.0)):
        assert not is_meta_row(row) and "no patch's row" in meta_row_refusal(row)
        with pytest.raises(ValueError, match="no patch's row"):
            t.add(row)
    assert t.set_desk([Binding("note:0:60", verb, "toggle")]) and not t.desk()
    assert meta_refusal(verb) is not None
    # (the meta controller's own rows pass: invariant, global layer, a key, a pad)
    for row in (Binding("note:0:61", verb, "toggle"), Binding("note:0:62", verb, "toggle", layer="global"),
                Binding("key:F9", verb, "fire"), Binding("pad:A", verb, "fire")):
        assert is_meta_row(row) and meta_row_refusal(row) is None


@pytest.mark.parametrize("carrier", [0, 1], ids=["on air carries", "off air carries"])
def test_a_preset_carrying_load_rows_reaches_no_other_deck(rig, carrier):
    """A file holding them all, loaded on either deck: the rows drop, with a note; its
    pressed control, its fired lanes and a whole pass move nothing on the other deck."""
    d, other = (rig.one, rig.two) if carrier == 0 else (rig.two, rig.one)
    _bank(rig, "party-wake", "party-tumble")
    put(rig.lib.home, "CARRIES",
        desk=[{"source": f"note:8:{k}", "target": v, "op": "toggle"}
              for k, v in enumerate(CARRIED)],
        routes=[{"source": f"seq:{k % 5}", "target": v, "op": "push", "value": 1.0}
                for k, v in enumerate(CARRIED)])
    d.presets.load("CARRIES")
    assert d.presets.current == "CARRIES"
    assert not [b for b in d.table.bindings if _library_verb(b.target) and not is_meta_row(b)]
    desk_notes = [n for n in d.presets.notes if n.startswith("dropped note:8:") and "no patch's row" in n]
    assert len(desk_notes) == len(CARRIED)
    assert all(any(f"→ {v}" in n for n in d.presets.notes) for v in CARRIED), "each route said"
    passing = NS(meta=rig.meta, chain=rig.r.chain)
    _pass(passing)
    theirs = _state(other)
    rig.meta.pointer("apc40").deck = d
    push(rig.r, *(note(k, channel=8) for k in range(len(CARRIED))))
    _pass(passing)
    assert _state(other) == theirs and d.presets.current == "CARRIES"


def test_a_learn_will_not_put_a_presets_row_on_a_library_verb(rig):
    """A desk Learn lands a preset-layer row, so it refuses, in words. A pad button's
    row is the meta controller's own, and takes one."""
    from hyperspace.ui_routing import desk_target, pad_target

    p = rig.one.reg["preset.next"]
    assert not desk_target(p) and pad_target(p)
    for pid in ("preset.save.0", "preset.save_new"):
        assert not desk_target(rig.one.reg[pid]) and pad_target(rig.one.reg[pid])
    # (row 746: a desk Learn on one lands a person's row: tests/test_layer_boundary.py)


SAVES = ["preset.save.0", "preset.save.7", "preset.save_new"]


@pytest.mark.parametrize("verb", SAVES)
def test_a_preset_cannot_carry_a_row_on_a_save_verb_by_any_door(verb):
    """A look's own row writing over another look's file breaks the absolute rule."""
    t = Bindings()
    for row in (Binding("note:0:60", verb, "toggle", layer="preset"),
                Binding("note:0:60", verb, "hold", layer="preset"),
                Binding("seq:0", verb, "push", 1.0), Binding("lfo:0", verb, "position", 1.0)):
        assert not is_meta_row(row) and "no patch's row" in meta_row_refusal(row)
        with pytest.raises(ValueError, match="no patch's row"):
            t.add(row)
    assert t.set_desk([Binding("note:0:60", verb, "toggle")]) and not t.desk()
    for row in (Binding("note:0:61", verb, "hold"), Binding("note:0:62", verb, "hold", layer="global"),
                Binding("key:SHIFT+F9", verb, "fire"), Binding("pad@edge:MENU", verb, "hold")):
        assert is_meta_row(row) and meta_row_refusal(row) is None


def _files(rig) -> dict:
    """Every preset file and the show's, byte for byte, with the bank."""
    home = rig.lib.home
    return {"files": {str(f): f.read_bytes() for f in home.rglob("*.json")},
            "bank": list(rig.one.presets.lib.project.bank)}


@pytest.mark.parametrize("carrier", [0, 1], ids=["on air carries", "off air carries"])
def test_a_preset_carrying_save_rows_loses_them_with_a_note_and_writes_nothing(rig, carrier):
    d = (rig.one, rig.two)[carrier]
    put(rig.lib.home, "SAVER",
        desk=[{"source": f"note:8:{k}", "target": v, "op": "toggle"} for k, v in enumerate(SAVES)],
        routes=[{"source": f"seq:{k}", "target": v, "op": "push", "value": 1.0}
                for k, v in enumerate(SAVES)])
    d.presets.load("SAVER")
    assert d.presets.current == "SAVER"
    assert not [b for b in d.table.bindings if _library_verb(b.target) and not is_meta_row(b)]
    for v in SAVES:
        assert any(n.startswith("dropped note:8:") and f"→ {v}" in n and "no patch's row" in n
                   for n in d.presets.notes), v
        assert any(n.startswith("dropped seq:") and v in n for n in d.presets.notes), v
    passing = NS(meta=rig.meta, chain=rig.r.chain)
    _pass(passing)
    before = _files(rig)
    rig.meta.pointer("apc40").deck = d
    push(rig.r, *(note(k, channel=8) for k in range(len(SAVES))))
    _pass(passing)
    assert _files(rig) == before


def test_the_panels_save_still_saves(rig):
    """The owner's "a save is not changed" is the person's: this, the two below."""
    rig.lib.save_as(PRESETS, "KEPT BY HAND")
    assert rig.lib.path_of(PRESETS, "KEPT BY HAND") is not None
    assert rig.one.presets.current == "KEPT BY HAND" and rig.two.presets.current == "TRIP"


def test_a_held_empty_pad_on_the_invariant_row_writes_its_file(rig):
    from hyperspace import midi

    project = rig.one.presets.lib.project
    empty = project.next_empty()
    n, ch = _clip(empty)
    row = next(b for b in rig.one.table.active() if b.target == "preset.select" and int(b.value) == empty)
    assert row.layer is None and meta_row_refusal(row) is None
    t = [0.0]
    rig.r.midi.clock = lambda: t[0]
    push(rig.r, note(n, channel=ch))
    t[0] = midi.HOLD_S + 0.01
    rig.r.midi.poll()
    assert rig.lib.path_of(PRESETS, project.bank[empty]) is not None


def test_the_edges_hold_to_save_still_saves(rig):
    """The Edge's factory row (row 723): `pad@edge:MENU`, a hold, the meta controller's."""
    row = Binding("pad@edge:MENU", "preset.save_new", "hold")
    assert is_meta_row(row) and rig.one.table.add(row) is row
    rig.one.table.primaries = {"pad": "edge"}
    listed = set(rig.lib.list(PRESETS))
    pad = ScriptedPad()
    for now in (1.0, 1.0 + routing.HOLD_S):      # the real road: held for `HOLD_S`
        pad.frame(held={gamepad.MENU})
        rig.one.router.pad(pad, now=now)
    assert len(set(rig.lib.list(PRESETS)) - listed) == 1


def test_no_factory_row_or_corpus_preset_carries_a_load_or_save_row():
    """The factory's load rows are all invariant and its save rows are keys, so the
    meta controller's; no corpus preset or shipped JSON's `desk` or `routes` has one."""
    rows = [b for b in factory_desk() if _library_verb(b.target)]
    assert len(rows) > 24 and all(b.layer is None for b in rows)
    assert all(is_meta_row(b) for b in Bindings.factory().bindings if _library_verb(b.target))
    root = Path(__file__).parent / "corpus"
    files = [*root.rglob("*.json"), *Path(app.__file__).parent.rglob("*.json")]
    assert files
    for f in files:
        try:
            doc = json.loads(f.read_text())
        except ValueError:
            continue
        if not isinstance(doc, dict):
            continue
        for row in (*(doc.get("desk") or ()), *(doc.get("routes") or ())):
            target = row.get("target") if isinstance(row, dict) else None
            assert not (target and _library_verb(target)), (f, row)


# --------------------------------------------------------- the frame and the panel

def test_the_crossfader_ticks_first_so_the_handles_read_the_deck_arriving(rig):
    """D5c's seam: the deck arriving must get this frame's `dim`, `bands` and
    `max_frame`, so `tick` is the frame's first act, before `h.reg`."""
    src = inspect.getsource(app.frame)
    assert src.index("h.meta.tick(now, dt)") < src.index("reg, keys, router, reloader = h.reg")
    assert src.index("h.meta.tick(now, dt)") < src.index("h.clock.tick(now)")
    assert "meta=meta" in inspect.getsource(app.main)
    assert "hold" not in inspect.signature(app._draw_render).parameters


def test_a_raising_tick_costs_the_frame_nothing():
    """(The guard every block of `frame` has: a hot reload's fix comes next save.)"""
    tree = ast.parse(inspect.getsource(app.frame))
    first = next(n for n in tree.body[0].body if isinstance(n, ast.If))
    assert any(isinstance(n, ast.Try) for n in first.body)


def test_the_media_page_reads_the_channels_of_the_panels_deck(rig):
    """D5c's seam: `media_of` read deck 1's whichever deck the panel was on."""
    one, two = NS(name="one"), NS(name="two")
    rig.one.reg.media, rig.two.reg.media = one, two
    panel = NS(media=NS(state=one), reg=rig.one.reg)
    assert ui_media.media_of(panel) is one
    panel.reg = rig.two.reg
    assert ui_media.media_of(panel) is two
    assert ui_media.media_of(NS(media=NS(state=one))) is one          # a stand-in's


def test_the_chase_on_the_deck_off_air_works_and_stays_there(rig):
    """Row 656 went with the hold: nothing refuses a press."""
    rig.two.reg[CHASE_PARAM].set(True)
    assert rig.two.reg.chasing and not rig.one.reg.chasing
    rig.two.reg[CHASE_PARAM].set(False)


@pytest.mark.parametrize("words", ["HOLD", "TAKE", "DROP", "projector is held", "preview"])
def test_no_tip_still_names_the_hold(rig, words):
    """REVIEW's "text matches the current model", over every param's own words."""
    for p in rig.one.reg:
        assert words not in (p.tip or ""), p.id


# ------------------------------------------------------- review of db415ae

def _caught_at_zero(tmp_path):
    """A 30-second fade asked from 0 with the desk's fader caught at 0, the first case."""
    r = boot(tmp_path / "home")
    two = Deck.beside(r.deck, lfos=lfo.LFOs(seed=1))
    meta = MetaController(r.deck, two, mix=r.mix)
    r.midi.point(meta.pointer("apc40"), meta.panel_pointer)
    push(r, cc(apc40.CC_XFADE, 0))
    (row,) = [b for b in r.midi.table.bindings if b.target == "output.xfade"]
    assert row.caught
    r.reg["output.xfade_s"].set(30.0)
    meta.crossfade()
    meta.tick(0.0, DT)
    return r, meta


def test_a_pots_jitter_caught_at_the_end_leaves_a_timed_fade_running(tmp_path):
    """Finding 1. One step, even a caught one, is written by nobody, and `tick` runs on."""
    r, meta = _caught_at_zero(tmp_path)
    for step in (0, 1, 0, 2, 1):
        push(r, cc(apc40.CC_XFADE, step))
        meta.tick(0.1, DT)
        assert meta.timed is not None
    meta.tick(15.0, DT)
    assert r.mix.xfade == pytest.approx(0.5, abs=0.01)
    meta.tick(31.0, DT)
    assert r.mix.xfade == 1.0
    undo.install(None)


def test_a_fader_resting_where_the_fade_passes_does_not_strand_it(tmp_path):
    """Finding 1. It would catch as the value crosses it, and end the fade between the ends."""
    r, meta = _timed_rig(tmp_path)
    (row,) = [b for b in r.midi.table.bindings if b.target == "output.xfade"]
    rest = 64
    push(r, cc(apc40.CC_XFADE, rest))
    for t, jitter in ((15.5, 65), (16.0, 64)):        # the value passes the pot's 0.5
        meta.tick(t, DT)
        r.midi.poll()
        push(r, cc(apc40.CC_XFADE, jitter))
        assert meta.timed is not None and not row.caught
    meta.tick(31.0, DT)
    assert r.mix.xfade == 1.0
    undo.install(None)


def test_a_real_move_still_ends_it_where_it_is(tmp_path):
    r, meta = _caught_at_zero(tmp_path)
    push(r, cc(apc40.CC_XFADE, 1), cc(apc40.CC_XFADE, 4))
    assert meta.timed is None
    undo.install(None)


def test_a_chip_click_moves_the_panel_after_the_page_is_drawn(rig):
    """Finding 2. `_arrive` is the page's last act; the frame's view stays one deck's."""
    st = {"panel_to": rig.two}
    panel = NS(meta=rig.meta)
    src = inspect.getsource(ui_graph.page)
    assert src.rindex("_arrive(panel, st)") > src.rindex("_canvas(panel, st, view")
    assert src.rindex("_arrive(panel, st)") > src.rindex("ui_pane.draw(panel, st, dt")
    assert "point_panel" not in inspect.getsource(ui_graph._deck_row)
    assert rig.meta.panel is rig.one
    ui_graph._arrive(panel, st)
    assert rig.meta.panel is rig.two and "panel_to" not in st
    ui_graph._arrive(panel, st)                       # once
    assert rig.meta.panel is rig.two


def test_a_layered_row_on_a_reserved_control_never_acts_its_row_disabled():
    """Finding 3: `dispatch`, `active` and the graph's shadow all ask what `is_invariant` says."""
    t = Bindings([Binding(f"cc:0:{apc40.CC_XFADE}", "output.xfade", "abs", enabled=False),
                  Binding(f"cc:0:{apc40.CC_XFADE}", "view.bright", "abs", layer="global"),
                  Binding("cc:0:1", "view.speed", "abs", layer="global")])
    t.set_layer("global")
    assert t.dispatch("cc", 0, apc40.CC_XFADE) == []
    assert [b.target for b in t.active() if b.layer == "global"] == ["view.speed"]
    assert t.is_invariant(t.bindings[1], [])
    other = Bindings([Binding(f"cc:0:{apc40.CC_XFADE}", "view.bright", "abs", layer="global")],
                     profile="generic")
    other.set_layer("global")
    assert [b.target for b in other.dispatch("cc", 0, apc40.CC_XFADE)] == ["view.bright"]


def test_the_words_after_a_press_name_cmd_z_only_where_it_is_true(rig):
    """Finding 4, as row 753 settled it. With the panel on air the words name no ⌘Z; with
    the panel on the deck off air the load is a push on the stack in focus, so ⌘Z does
    take it back; a mouse in a meta section is ⌘Z elsewhere, so they do not say so."""
    _bank(rig, "party-wake", "party-tumble")
    n = len(rig.one.undo.stack)
    rig.one.reg["preset.load.0"].fire()
    assert undo.here() is rig.one.undo and len(rig.one.undo.stack) == n
    assert rig.lib.status.endswith("the room still sees deck 1")
    _quiet(rig.two)
    rig.meta.point_panel(rig.two)
    assert undo.here() is rig.two.undo
    rig.one.reg["preset.load.1"].fire()
    assert rig.lib.status.endswith("; ⌘Z takes it back")
    now = rig.two.presets.current
    rig.r.reg["edit.undo"].fire()
    assert rig.two.presets.current != now
    undo.where(lambda: True)
    rig.one.reg["preset.load.1"].fire()
    assert rig.lib.status.endswith("the room still sees deck 1")


def test_a_generic_table_gains_no_apc_rows():
    """Finding 5."""
    rows, notes = routing.remap_factory([], "generic")
    assert not [b for b in rows if b.is_midi] and not [n for n in notes if "APC40" in n]
    rows, _ = routing.remap_factory([], "apc40")
    assert any(b.target == "preset.select" for b in rows)


def test_a_click_on_the_fade_chip_during_a_run_does_nothing(rig):
    """Finding 6: not a restart, and past the middle not a way back."""
    meta = rig.meta
    rig.one.reg["output.xfade_s"].set(10.0)
    meta.crossfade()
    meta.tick(0.0, DT)
    meta.tick(7.0, DT)
    assert meta.on_air is rig.two
    run = meta.timed
    meta.crossfade()
    assert meta.timed is run
    meta.tick(11.0, DT)
    assert rig.mix.xfade == 1.0 and meta.on_air is rig.two
    meta.crossfade()                                  # and home, once it has arrived
    assert meta.timed is not None and meta.timed.to == 0.0


def test_a_load_with_nowhere_to_land_is_refused_never_this_deck(rig):
    """Finding 7: it fails closed."""
    project = rig.one.presets.lib.project
    _bank(rig, "party-wake")
    project.meta = NS(row_load=lambda: (None, None))
    theirs = _state(rig.one)
    rig.lib.warning = ""
    assert project.load_slot(0) is None
    assert _state(rig.one) == theirs and "not loaded" in rig.lib.warning


def test_the_leftover_words_are_gone():
    """Finding 8."""
    from hyperspace import replay

    assert "held PROJECTOR" not in replay.__doc__ and "ON AIR inset" in replay.__doc__
    assert "output.dim" in meta_row_refusal.__doc__


def test_is_invariant_parses_nothing_once_it_has_seen_a_control(rig, monkeypatch):
    """Finding 9: per port and per setter row, so no `Binding` is built on the warm road."""
    table, b = Bindings(), Binding(f"cc:0:{apc40.CC_XFADE}", "view.bright", "abs", layer="global")
    assert table.is_invariant(b)

    def built(*a, **k):
        raise AssertionError("parsed again")

    monkeypatch.setattr(routing, "Binding", built)
    assert table.is_invariant(b)


def test_names_is_settles_one_road(rig):
    """Finding 10: `spec` None is no instances, `fx` an empty set; there is no fallback."""
    gs = rig.one.presets.graph
    assert gs.names(None)["fx"] == frozenset() and "spec" in inspect.signature(gs.names).parameters
    assert inspect.signature(gs.names).parameters["spec"].default is inspect.Parameter.empty
