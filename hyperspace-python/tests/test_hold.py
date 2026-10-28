"""Plan 38: the hold — the projector keeps its look while the operator
builds the next one (hyperspace/hold.py).

Headless first, over the app's own objects (`test_undo.boot`): what is
held, the program's values around a draw and the live ones after, a
modulated param riding on its held base, Take, Drop as an undo step back
to the hold point (the preset's part only, the graph included), the
`output.*` controls. Then `app._draw_render` with stand-ins: the program
drawn inside the hold, the preview after it, the monitor on output 1.
Then on GL: the program is the held frame byte for byte while the
preview shows the edit, and Take puts the edit on the outputs."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from test_undo import boot, frames, settle

from hyperspace import graph as G
from hyperspace import hold as H
from hyperspace.graph import Wiring

DT = 1 / 60


@pytest.fixture()
def rig(tmp_path):
    r = boot(tmp_path / "home")
    # plan 38 B1: the renderer as plan 36 leaves it — the empty frame until
    # a preset's graph lands one, the open show's rig cables (`rig_source`)
    r.renderer = SimpleNamespace(wiring=G.EMPTY, ghost_states={}, rig_source=r.lib.project)
    r.presets.graph.attach(r.renderer)
    r.hold = H.Hold(r.reg, r.renderer, undo=r.undo)
    settle(r)
    return r


def test_only_the_looks_render_params_are_held(rig):
    """The groups the renderer reads, persisted, real, set — not the turn's
    3D switch, the rig, the modulators or a trigger."""
    rig.hold.engage()
    held = set(rig.hold.values)
    # (plan 36: an effect's own params exist only while a preset wires it —
    # the startup preset wires none — so the effects' group is `fx.mix`'s)
    assert {"view.bright", "view.lines", "camera.zoom", "fx.mix",
            "dream.mix", "pattern.mod.1"} <= held
    assert not {p for p in held if p.split(".")[0] in ("lfo", "media", "tempo", "output",
                                                       "hands", "eye", "rot", "macro")}
    assert "view.three_d" not in held
    assert all(rig.reg[p].persist and not rig.reg[p].alias for p in held)


def test_the_program_draws_the_held_look_and_the_live_one_comes_back(rig):
    """Engaged, a knob turned is the preview's: its base moves as ever (the
    dirty dot, undo), the program's draw sees the held value, the object
    holds the live one again after — even when the draw raises."""
    reg, hold, view = rig.reg, rig.hold, rig.view
    reg["view.bright"].set(1.0)
    hold.engage(now=5.0)
    reg["view.bright"].set(0.25)
    reg["view.lines"].set(False)
    frames(rig)
    assert sorted(hold.changed()) == ["view.bright", "view.lines"]
    with hold.program():
        assert view.bright == 1.0 and view.lines is True
    assert view.bright == 0.25 and view.lines is False and hold.moved == 2
    with pytest.raises(RuntimeError), hold.program():
        raise RuntimeError("boom")
    assert view.bright == 0.25 and reg["view.bright"].base == 0.25


def test_the_program_takes_the_held_wiring_and_hands(rig):
    """The renderer's wiring and extra hands states are the program's for
    the draw, the live ones after; `rewired` says the graph moved."""
    r, hold = rig.renderer, rig.hold
    held_w = r.wiring
    hold.engage()
    assert not hold.rewired()
    blank = Wiring(wired=True)
    r.wiring, r.ghost_states = blank, {"ghost.2": object()}
    assert hold.rewired()
    with hold.program():
        assert r.wiring is held_w and r.ghost_states == {}
    assert r.wiring is blank and set(r.ghost_states) == {"ghost.2"}


def test_a_bus_cable_cut_after_the_hold_stays_off_the_projector(rig):
    """Plan 38 B1 (plan 36's explicit graph): the rig's bus cables are part
    of what is held. A cable cut on GRAPH after the press — the open show's
    `RigWires` — is the preview's: the program reads the cables as they
    stood (by `graph.rig_of`, as `Renderer._graph_for` does), the live ones
    come back after the draw, `rewired` says the graph moved, and the
    preview renderer reads the cut, never a default."""
    r, hold, show = rig.renderer, rig.hold, rig.lib.project
    assert show.rig == G.RigWires()
    hold.engage()
    show.rig = show.rig.cutting(G.bus_wire(1, "image"))
    assert hold.rewired()
    with hold.program():
        assert G.rig_of(r.rig_source) == G.RigWires()
        assert r.wiring is hold.wiring
    assert r.rig_source is show and G.rig_of(r.rig_source).cut == {G.bus_wire(1, "image")}
    pr = SimpleNamespace(ghost=None)
    H.mirror(r, pr)
    assert pr.rig_source is show and pr.wiring is r.wiring
    assert hold.take() and not hold.rewired()
    with hold.program():
        assert G.rig_of(r.rig_source).cut == {G.bus_wire(1, "image")}


def test_drop_puts_a_bus_cable_cut_during_the_hold_back(rig):
    """A bus cable cut is a graph edit, so Drop's one undo step stands it
    again (the show's mark carries the rig's wires, plan 36 T1): the
    projector, which never saw the cut, still never moves."""
    show = rig.lib.project
    rig.hold.engage()
    show.rig = show.rig.cutting(G.bus_wire(1, "image"))
    settle(rig)
    assert rig.hold.drop()
    settle(rig)
    assert show.rig == G.RigWires()
    assert rig.undo.undo() and show.rig.cut == {G.bus_wire(1, "image")}


def test_a_modulated_param_rides_its_held_base(rig):
    """The bands and the LFOs drive the program too: its value is the held
    base plus the offset the live base got this frame."""
    reg, hold = rig.reg, rig.hold
    p = reg["view.bright"]
    p.set(p._value_of_norm(0.5))
    hold.engage()
    p.set(p._value_of_norm(0.2))           # the operator's
    p.modulate(0.1)                        # a band's, this frame
    reg.apply()
    assert p.eff_norm == pytest.approx(0.3)
    with hold.program():
        assert p.eff_norm == pytest.approx(0.6)
    assert p.eff_norm == pytest.approx(0.3) and p._norm_of(p.base) == pytest.approx(0.2)


def test_an_unmoved_param_costs_nothing(rig):
    hold = rig.hold
    hold.engage()
    with hold.program():
        pass
    assert hold.moved == 0 and hold.changed() == []


def test_take_lets_go_and_the_program_is_what_is_landed(rig):
    reg, hold, view = rig.reg, rig.hold, rig.view
    hold.engage()
    reg["view.bright"].set(0.3)
    assert hold.take() and not hold.on and not hold.take()
    with hold.program():
        assert view.bright == 0.3
    assert reg["view.bright"].base == 0.3


def test_drop_goes_back_to_the_hold_point_as_one_undo_step(rig):
    """Drop: the look and the graph as they were at HOLD, the rig's params
    left; one step, and undoing it brings the edits back."""
    reg, hold, r = rig.reg, rig.hold, rig.renderer
    from hyperspace.graph import read_graph

    zoom0, fov0 = reg["camera.zoom"].base, reg["eye.fov"].base
    wiring0 = r.wiring
    hold.engage()
    reg["camera.zoom"].set(zoom0 * 2)
    reg["eye.fov"].set(fov0 + 10)          # the room's, not the look's
    rig.presets.graph.land(read_graph({"frame": "wired"}))
    settle(rig)
    assert r.wiring != wiring0 and hold.rewired()
    assert hold.drop() and not hold.on
    settle(rig)
    assert reg["camera.zoom"].base == pytest.approx(zoom0)
    assert reg["eye.fov"].base == pytest.approx(fov0 + 10)
    assert r.wiring == wiring0
    assert rig.undo.undo()
    assert reg["camera.zoom"].base == pytest.approx(zoom0 * 2)
    assert r.wiring != wiring0


def test_drop_without_undo_puts_the_held_params_back(rig):
    hold = H.Hold(rig.reg, rig.renderer)
    b0 = rig.reg["view.bright"].base
    hold.engage()
    rig.reg["view.bright"].set(0.1)
    assert hold.drop()
    assert rig.reg["view.bright"].base == pytest.approx(b0)


def test_the_output_controls(rig):
    """`output.hold` holds and takes, `output.take` and `output.drop` fire;
    rig params: never persisted, not modulatable, lit while held."""
    reg, hold = rig.reg, rig.hold
    H.register(reg, hold, now=lambda: 7.0)
    p = reg["output.hold"]
    assert not p.persist and not p.modulatable and p.group == "output"
    p.set(True)
    assert hold.on and hold.since == 7.0 and reg["output.take"].get()
    p.set(False)
    assert not hold.on and not reg["output.drop"].get()
    b0 = reg["view.bright"].base
    p.set(True)
    reg["view.bright"].set(0.4)
    reg["output.drop"].fire()
    assert not hold.on and reg["view.bright"].base == pytest.approx(b0)
    p.set(True)
    reg["output.take"].fire()
    assert not hold.on


def test_preview_size_keeps_the_aspect_under_both_caps():
    assert H.preview_size((800, 500)) == (800, 500)
    assert H.preview_size((3840, 2160)) == (1280, 720)
    assert H.preview_size((3840, 2160), (1920, 1080)) == (1280, 720)
    assert H.preview_size((1000, 2000), (500, 500)) == (250, 500)


def test_the_preview_renderer_reads_what_the_main_one_does():
    main = SimpleNamespace(media="m", cloud_source="c", bands=(0.5,), ghost_states=None,
                           wiring="w", rig_source="show", ghost=SimpleNamespace(source="hands", router="table"),
                           max_frame=(10, 10), bg_alpha=0.2, dim=0.3)
    pr = SimpleNamespace(ghost=SimpleNamespace(source=None, router=None))
    H.mirror(main, pr)
    assert (pr.media, pr.cloud_source, pr.bands, pr.wiring) == ("m", "c", (0.5,), "w")
    assert pr.rig_source == "show"          # plan 38 B1: the bus as the show has it
    assert pr.ghost_states == {} and (pr.ghost.source, pr.ghost.router) == ("hands", "table")
    assert (pr.max_frame, pr.bg_alpha, pr.dim) == (None, 1.0, 1.0)


def test_a_preview_that_raises_costs_nothing_but_says_so(rig):
    class Boom:
        def draw_outputs(self, *a, **k):
            raise RuntimeError("no GL")

    rig.hold.make = Boom
    rig.hold.engage()
    assert not rig.hold.draw_preview(rig.view, 640, 400, (640, 400), None,
                                     lambda sz, t: None)
    assert "no GL" in rig.hold.error
    rig.hold.make = lambda: (_ for _ in ()).throw(ValueError("no context"))
    rig.hold.preview = None
    assert rig.hold.preview_renderer() is None and "no context" in rig.hold.error


def test_the_head_line_says_how_long_and_what_changed(rig):
    from hyperspace.ui_graph import hold_line

    hold = rig.hold
    hold.engage(now=100.0)
    assert hold_line(hold, 165.0).startswith("HELD 1:05")
    assert hold_line(hold, 165.0).endswith("nothing changed yet")
    rig.reg["view.bright"].set(0.5)
    rig.renderer.wiring = Wiring(wired=True)
    line = hold_line(hold, 165.0)
    assert "1 setting changed" in line and "the graph changed" in line


# ---- plan 38 B2: the hand checks the controller can run headless


def test_drop_after_a_whole_new_look_is_one_undo_step_back_and_one_forward(rig):
    """Hand check AI.4, headless (plan 38 B2). Held on a clean TUMBLE: three
    of the look's params moved, the graph rewired on GRAPH, another preset
    loaded (TRIP: other values, routes, desk, graph), its macros and a
    route edited, a rig param (the eye's) moved. DROP: the values, the
    graph, the routes, the desk's preset layer, the macros and the name are
    the hold point's — the dirty dot out as it was — and the rig's param is
    left. One step: the stack grows by one, and one ⌘Z brings the whole
    dropped state back (TRIP, edited, dirty), the rig's param still left."""
    from test_undo import look, same_look

    from hyperspace.graph import read_graph
    from hyperspace.library import PRESETS

    reg, lib, hold, r, table = rig.reg, rig.lib, rig.hold, rig.renderer, rig.table
    rig.undo.clear()
    assert lib.current(PRESETS) == "TUMBLE" and not lib.is_dirty(PRESETS)
    at_hold, wiring0, fov0 = look(rig), r.wiring, reg["eye.fov"].base
    hold.engage()
    for pid, k in (("view.bright", 3), ("camera.zoom", 4), ("fx.mix", -5)):
        reg[pid].step(k)
    settle(rig)
    rig.presets.graph.land(read_graph({"frame": "wired"}))     # a GRAPH edit
    settle(rig)
    reg["preset.load.4"].fire()                                # another preset
    settle(rig)
    assert lib.current(PRESETS) == "TRIP"
    table.set_macros({"macro.1": {"label": "mine", "subs": [
        {"base": "view.speed", "from": 0.2, "to": 0.9}]}}, reg)
    table.remove(table.routes()[0])
    reg["eye.fov"].set(fov0 + 10)                              # the room's, not the look's
    settle(rig)
    assert lib.is_dirty(PRESETS) and hold.rewired()
    dropped, wiring1, depth = look(rig), r.wiring, len(rig.undo.stack)
    assert not same_look(dropped, at_hold) and wiring1 != wiring0
    assert all(a != b for a, b in zip(at_hold[1:], dropped[1:], strict=True))

    assert hold.drop() and not hold.on
    assert same_look(look(rig), at_hold) and r.wiring == wiring0
    assert lib.current(PRESETS) == "TUMBLE" and not lib.is_dirty(PRESETS)
    assert reg["eye.fov"].base == pytest.approx(fov0 + 10)
    assert len(rig.undo.stack) == depth + 1 and rig.undo.stack[-1].label == "drop the preview"
    settle(rig)
    assert same_look(look(rig), at_hold) and r.wiring == wiring0   # nothing re-lands

    assert rig.undo.undo()                                     # one step, not several
    assert same_look(look(rig), dropped) and r.wiring == wiring1
    assert lib.current(PRESETS) == "TRIP" and lib.is_dirty(PRESETS)
    assert reg["eye.fov"].base == pytest.approx(fov0 + 10)
    assert len(rig.undo.stack) == depth


def test_learned_desk_buttons_light_while_held(rig):
    """Hand check AI.5, headless (plan 38 B2): `output.hold` and
    `output.take` learned onto the two free APC40 buttons (a press on each
    while armed, as at the desk, lands a preset-layer row). A press on hold
    holds and both LEDs go on; a press on take lets go and both go dark.
    Held again, DROP (from the panel) puts both out too."""
    from test_midi import note, push

    H.register(rig.reg, rig.hold, now=lambda: rig.t)
    free = (0x3C, 0x3D)                        # unbound on the startup desk
    assert not any(rig.table.route("note", 0, n) for n in free)
    for pid, n in zip(("output.hold", "output.take"), free, strict=True):
        rig.learn.arm(pid)
        push(rig, note(n), note(n, 0))
        assert rig.learn.learning is None and not rig.learn.refused, rig.learn.last
        assert [b.target for b in rig.table.route("note", 0, n)] == [pid]
    assert not rig.hold.on                     # a learning press does not fire

    def leds():
        on = {}
        for m in rig.out.sent:
            if m.type in ("note_on", "note_off") and m.channel == 0 and m.note in free:
                on[m.note] = m.type == "note_on" and m.velocity > 0
        return tuple(on.get(n, False) for n in free)

    rig.midi.poll()
    assert leds() == (False, False)
    push(rig, note(free[0]), note(free[0], 0))                 # hold
    rig.midi.poll()
    assert rig.hold.on and leds() == (True, True)
    push(rig, note(free[1]), note(free[1], 0))                 # take
    rig.midi.poll()
    assert not rig.hold.on and leds() == (False, False)
    assert rig.hold.status.startswith("taken")
    push(rig, note(free[0]), note(free[0], 0))                 # hold again
    rig.midi.poll()
    assert rig.hold.on and leds() == (True, True)
    rig.reg["output.drop"].fire()
    rig.midi.poll()
    assert not rig.hold.on and leds() == (False, False)
    assert rig.hold.status.startswith("dropped")


# ---- app._draw_render with the hold (stand-ins, test_app_boundary's)


def test_held_the_outputs_draw_the_program_and_the_preview_follows(monkeypatch):
    """Held: every output in one `draw_outputs` inside `Hold.program`; the
    page's backdrop is the preview, drawn after by the hold into the
    preview's tap at the preview's size, published to it, output 1's window
    bound again; output 1 rides the monitor; one flush."""
    from test_app_boundary import _Ctx, _rig_slots, _SwapGlfw

    from hyperspace import app
    from hyperspace.outputs import Preview

    log: list[str] = []
    monkeypatch.setattr(app, "glfw", _SwapGlfw(log, {"w1": (1600, 1000)}))

    class R:
        bg_alpha, max_frame = 1.0, None

        def __init__(self):
            self.wiring, self.ghost_states, self.calls = "live", {}, []

        def draw_outputs(self, s, w, h, dpr, views, t_now=None):
            self.calls.append((self.wiring, views, dpr))
            log.append(f"draw {self.wiring}")

    class Tap:
        tex = "tap-tex"

        def fit(self, size):
            log.append(f"fit {size}")
            return "fbo"

    main, pr = R(), R()
    hold = H.Hold(SimpleNamespace(get=lambda pid: None), main, make=lambda: pr)
    hold.on, hold.wiring = True, "held"
    preview, monitor = Preview(), Preview()
    preview.tap, monitor.tap = Tap(), object()
    preview.want()
    monitor.want()
    app._draw_render(main, _Ctx(log), object(), _rig_slots("x"),
                     flush=lambda: log.append("flush"), preview=preview, hold=hold,
                     monitor=monitor)
    (wiring, views, _), = main.calls
    assert wiring == "held" and main.wiring == "live"
    assert views[0].publish == [monitor] and views[0].tap is monitor.tap
    (pw, pviews, dpr), = pr.calls
    assert pw == "live" and pviews[0].target == "fbo" and pviews[0].size == (1280, 800)
    assert dpr == pytest.approx(1280 / 1600)
    assert preview.tex == "tap-tex" and not preview.wanted and not monitor.wanted
    assert log.index("draw held") < log.index("fit (1280, 800)") < log.index("draw live")
    assert log[log.index("draw live") + 1] == "bind screen" and log.count("flush") == 1


def test_held_with_the_page_closed_draws_no_preview(monkeypatch):
    from test_app_boundary import _Ctx, _rig_slots, _SwapGlfw

    from hyperspace import app
    from hyperspace.outputs import Preview

    log: list[str] = []
    monkeypatch.setattr(app, "glfw", _SwapGlfw(log))
    made = []
    main = SimpleNamespace(bg_alpha=1.0, wiring="live", ghost_states={},
                           draw_outputs=lambda *a, **k: log.append(f"draw {main.wiring}"))
    hold = H.Hold(SimpleNamespace(get=lambda pid: None), main, make=lambda: made.append(1))
    hold.on, hold.wiring = True, "held"
    app._draw_render(main, _Ctx(log), object(), _rig_slots("x"), flush=lambda: log.append("f"),
                     preview=Preview(), hold=hold, monitor=Preview())
    assert log.count("draw held") == 1 and not made and "f" not in log


# ---- on GL: the program is the held frame, the preview the edit

moderngl = pytest.importorskip("moderngl")


@pytest.fixture(scope="module")
def ctx():
    try:
        c = moderngl.create_context(standalone=True)
    except Exception as e:  # noqa: BLE001 — any GL failure means skip
        pytest.skip(f"no standalone GL context available: {e}")
    yield c
    c.release()


def test_on_gl_the_projector_keeps_the_held_frame_while_the_preview_shows_the_edit(ctx):
    """The default frame held; the operator lands a new preset (nothing
    wired: black) and turns the brightness down. The program draw is the
    held frame byte for byte (as drawn before the hold); the preview is
    black; after Take the outputs are black too."""
    import numpy as np
    from test_outputs import H as HH
    from test_outputs import W, fbo, px, scene_view

    from hyperspace.control import Control
    from hyperspace.graphmigrate import wiring_of
    from hyperspace.outputs import Switches, View
    from hyperspace.params import build_registry
    from hyperspace.render import Renderer

    r = Renderer(ctx)
    r.wiring = wiring_of(r.fx.state)
    s = scene_view()
    from hyperspace.analysis import Analyser
    from hyperspace.analyzer import Analyzer

    chain = Analyzer(Analyser())
    reg = build_registry(s, Control(chain), SimpleNamespace(chain=chain), None,
                         dream=r.lookback.state, fx=r.fx.state)
    hold = H.Hold(reg, r, make=lambda: H.preview_renderer(r))
    out = fbo(ctx)

    def program(t):
        with hold.program():
            r.draw_outputs(s, W, HH, 1.0, [View(Switches(), (W, HH), target=out)], t_now=t)
        return px(ctx, out)

    before = program(2.0)
    assert before[..., :3].max() > 0
    hold.engage()
    r.wiring = Wiring(wired=True)
    reg["view.bright"].set(0.2)
    held = program(2.0)
    assert np.array_equal(held, before)
    assert r.wiring == Wiring(wired=True) and s.bright == pytest.approx(0.2)
    pv = fbo(ctx)
    assert hold.draw_preview(s, W, HH, (W, HH), pv,
                             lambda sz, t: View(Switches(), sz, target=t))
    assert px(ctx, pv)[..., :3].max() == 0
    assert hold.take()
    assert program(2.0)[..., :3].max() == 0
    assert ctx.error == "GL_NO_ERROR"


@pytest.mark.empty_frame        # the app's own renderers: nothing until a graph lands
def test_on_gl_a_bus_cable_cut_after_the_hold_stays_off_the_projector(ctx):
    """Plan 38 B1, on GL with plan 36's explicit graph: the scene reaches
    output 1 only by the rig's bus cable from All outputs. Held, the cable
    is cut on GRAPH: the program draws the held frame byte for byte (the
    held cables, the held wiring, the same graph), the preview renderer —
    built on the same context, reading the show's cables — draws the cut
    (black), and after Take so do the outputs."""
    import numpy as np
    from test_outputs import H as HH
    from test_outputs import W, fbo, px, scene_view

    from hyperspace.control import Control
    from hyperspace.graphmigrate import wiring_of
    from hyperspace.outputs import Switches, View
    from hyperspace.params import build_registry
    from hyperspace.render import Renderer

    r = Renderer(ctx)
    assert r.wiring == G.EMPTY and r.rig_source is None      # plan 36: no fill-in
    r.wiring = wiring_of(r.fx.state)
    assert G.Wire("scene", "output.all.image") in r.wiring.wires
    show = SimpleNamespace(rig=G.RigWires())
    r.rig_source = show
    s = scene_view()
    from hyperspace.analysis import Analyser
    from hyperspace.analyzer import Analyzer

    chain = Analyzer(Analyser())
    reg = build_registry(s, Control(chain), SimpleNamespace(chain=chain), None,
                         dream=r.lookback.state, fx=r.fx.state)
    hold = H.Hold(reg, r, make=lambda: H.preview_renderer(r))
    out = fbo(ctx)

    def program(t):
        with hold.program():
            r.draw_outputs(s, W, HH, 1.0, [View(Switches(), (W, HH), target=out)], t_now=t)
        return px(ctx, out)

    before = program(2.0)
    assert before[..., :3].max() > 0
    graph = r._graph
    hold.engage()
    show.rig = show.rig.cutting(G.bus_wire(1, "image"))
    assert hold.rewired()
    assert np.array_equal(program(2.0), before) and r._graph is graph
    assert r.rig_source is show
    pv = fbo(ctx)
    assert hold.draw_preview(s, W, HH, (W, HH), pv,
                             lambda sz, t: View(Switches(), sz, target=t))
    pr = hold.preview
    assert pr.rig_source is show and pr._graph.rig == show.rig
    assert px(ctx, pv)[..., :3].max() == 0
    assert hold.take()
    assert program(2.0)[..., :3].max() == 0 and r._graph.rig == show.rig
    assert ctx.error == "GL_NO_ERROR"


@pytest.mark.empty_frame        # the app's own renderers: nothing until a graph lands
def test_on_gl_the_program_draws_the_held_wiring_while_a_graph_edit_lands(ctx):
    """Hand checks AI.1 and AI.2, headless (plan 38 B2). Wiring W1 (today's
    frame) landed through the preset's `GraphSection`; held; then the GRAPH
    page's own edit (`graphview.Edit.insert_effect`: kaleido onto the cable
    scene → All outputs) lands W2. With the renderer drawing, the outputs'
    picture is W1's and the preview's W2's, each byte for byte the frame
    its wiring draws alone, on the same renderers at the same clock: W1's
    from before the hold, W2's from after Take. The two differ, so the
    edit shows."""
    import numpy as np
    from test_outputs import H as HH
    from test_outputs import W, fbo, px, scene_view

    from hyperspace import graphmigrate, graphview
    from hyperspace.control import Control
    from hyperspace.outputs import Switches, View
    from hyperspace.params import build_registry
    from hyperspace.preset import GraphSection
    from hyperspace.render import Renderer

    T = 2.0
    r = Renderer(ctx)
    r.rig_source = SimpleNamespace(rig=G.RigWires())
    s = scene_view()
    from hyperspace.analysis import Analyser
    from hyperspace.analyzer import Analyzer

    chain = Analyzer(Analyser())
    reg = build_registry(s, Control(chain), SimpleNamespace(chain=chain), None,
                         dream=r.lookback.state, fx=r.fx.state)
    gs = GraphSection(reg, fx=r.fx.state, renderer=r)
    doc1 = {"frame": "wired", **graphmigrate.section_of(graphmigrate.wiring_of(r.fx.state))}
    gs.land(G.read_graph(doc1), doc1)
    w1 = r.wiring
    assert G.Wire("scene", "output.all.image") in w1.wires
    hold = H.Hold(reg, r, make=lambda: H.preview_renderer(r))
    out = fbo(ctx)

    def outputs():
        with hold.program():
            r.draw_outputs(s, W, HH, 1.0, [View(Switches(), (W, HH), target=out)], t_now=T)
        return px(ctx, out)

    alone1 = outputs()
    assert alone1[..., :3].max() > 0
    hold.engage()
    edit = graphview.Edit(graph=gs)
    assert edit.insert_effect(("scene", "output.all.image"), "kaleido") is None
    w2 = r.wiring
    assert w2 != w1 and G.Wire("kaleido", "output.all.image") in w2.wires
    assert hold.rewired() and hold.wiring is w1

    held = outputs()
    assert np.array_equal(held, alone1) and r.wiring is w2
    pr = hold.preview_renderer()
    pr.now = lambda t_now=None: T          # the preview's clock pinned, as the outputs' is
    pv = fbo(ctx)
    assert hold.draw_preview(s, W, HH, (W, HH), pv,
                             lambda sz, t: View(Switches(), sz, target=t))
    preview = px(ctx, pv)
    assert pr.wiring is w2

    assert hold.take()
    alone2 = outputs()
    assert np.array_equal(preview, alone2)
    assert not np.array_equal(alone1, alone2)
    assert ctx.error == "GL_NO_ERROR"
