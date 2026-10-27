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

from hyperspace import hold as H
from hyperspace.graph import Wiring

DT = 1 / 60


@pytest.fixture()
def rig(tmp_path):
    r = boot(tmp_path / "home")
    r.renderer = SimpleNamespace(wiring=Wiring(), ghost_states={})
    r.presets.graph.attach(r.renderer)
    r.hold = H.Hold(r.reg, r.renderer, undo=r.undo)
    settle(r)
    return r


def test_only_the_looks_render_params_are_held(rig):
    """The groups the renderer reads, persisted, real, set — not the turn's
    3D switch, the rig, the modulators or a trigger."""
    rig.hold.engage()
    held = set(rig.hold.values)
    assert {"view.bright", "view.lines", "camera.zoom", "fx.warp.amount",
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


def test_a_modulated_param_rides_its_held_base(rig):
    """The bands and the LFOs drive the program too: its value is the held
    base plus the offset the live base got this frame."""
    reg, hold, view = rig.reg, rig.hold, rig.view
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
    reg, hold, view, r = rig.reg, rig.hold, rig.view, rig.renderer
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
                           wiring="w", ghost=SimpleNamespace(source="hands", router="table"),
                           max_frame=(10, 10), bg_alpha=0.2, dim=0.3)
    pr = SimpleNamespace(ghost=SimpleNamespace(source=None, router=None))
    H.mirror(main, pr)
    assert (pr.media, pr.cloud_source, pr.bands, pr.wiring) == ("m", "c", (0.5,), "w")
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
    from test_outputs import W, H as HH, fbo, px, scene_view

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
