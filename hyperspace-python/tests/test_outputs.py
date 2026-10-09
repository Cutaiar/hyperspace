"""Plan 21: the compose path — a picture per output on one GL context.

The pure half first (`outputs.route`, `outputs.fit`, the module's
imports), then the renderer's half on offscreen targets standing in for
the windows: the default view is today's frame byte for byte, every
switch state shows its picture, the scene pass, the capture and the
hands' layer run once a frame and the effect chain once per distinct
pipeline, and a failing view, pipeline or hands pass never costs the
other views, the first target's binding or the dim.

The pictures are offscreen renders from synthetic hands (fake_hands);
no window, screen or tracker is involved.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from hyperspace import outputs as O
from hyperspace.outputs import HANDS, SCENE, SCENE_HANDS, Switches, fit, route

# ---------------------------------------------------------------- no GL


def test_route():
    """Every row of the plan's table ("The frame as it will be"): with the
    through switch off, or no effect on, or no hand shown, the hands go
    over the finished frame or nowhere."""
    for fx_on in (False, True):
        for through in (False, True):
            def r(scene, hands, visible, through=through, fx_on=fx_on):
                return route(Switches(scene=scene, hands=hands, through=through), fx_on, visible)

            # scene on
            assert r(True, False, True) == (SCENE, False)        # hands switch off
            assert r(True, True, False) == (SCENE, False)        # no hand shows
            # scene off
            assert r(False, False, True) == (None, False)
            assert r(False, True, False) == (None, False)
            if not (through and fx_on):
                assert r(True, True, True) == (SCENE, True)      # hands over the effects
                assert r(False, True, True) == (None, True)      # hands alone on the ground
    # hands through effects (WP2): only with an effect on and a hand shown
    thru = Switches(through=True)
    assert route(thru, True, True) == (SCENE_HANDS, False)
    assert route(Switches(scene=False, through=True), True, True) == (HANDS, False)   # F2
    assert route(thru, False, True) == (SCENE, True)              # no effect: hands over
    assert route(thru, True, False) == (SCENE, False)             # no hand: nothing extra
    assert route(Switches(hands=False, through=True), True, True) == (SCENE, False)
    assert route(Switches(scene=False, hands=False, through=True), True, True) == (None, False)
    # the dim never routes
    assert route(Switches(dim=0.0), True, True) == route(Switches(), True, True)
    assert {SCENE, SCENE_HANDS, HANDS} == {0, 1, 2} and O.PIPELINES == (0, 1, 2)
    assert O.MAX_OUTPUTS == 4


def test_capped_shrinks_to_the_box_keeping_the_aspect_and_never_grows():
    assert O.capped((3840, 2160), (1920, 1080)) == (1920, 1080)        # 2× HiDPI 1080p
    assert O.capped((3840, 2400), (1920, 1080)) == (1728, 1080)        # 16:10: height binds
    assert O.capped((3456, 1956), (1920, 1080)) == (1908, 1080)
    assert O.capped((1280, 800), (1920, 1080)) == (1280, 800)          # inside: unchanged
    assert O.capped((3840, 2160), None) == (3840, 2160)                # full: no cap
    assert O.capped((0, 0), (1920, 1080)) == (1, 1)


def test_fit():
    assert fit((640, 400), (640, 400)) == (0, 0, 640, 400)
    assert fit((1920, 1080), (1280, 720)) == (0, 0, 1280, 720)          # same aspect: scaled
    assert fit((1600, 900), (1600, 1200)) == (0, 150, 1600, 900)        # letterbox: bars top/bottom
    assert fit((1600, 900), (800, 900)) == (0, 225, 800, 450)
    assert fit((900, 1600), (1600, 900)) == (547, 0, 506, 900)          # pillarbox
    x, y, w, h = fit((1920, 1080), (1024, 768))
    assert (w, h) == (1024, 576) and (x, y) == (0, 96)
    assert abs(w / h - 1920 / 1080) < 0.01
    assert fit((0, 0), (300, 200)) == (0, 0, 300, 200)                  # degenerate: the whole
    for src, dst in (((7, 3), (5, 11)), ((1, 1000), (1000, 1))):        # always inside dst
        x, y, w, h = fit(src, dst)
        assert x >= 0 and y >= 0 and w >= 1 and h >= 1 and x + w <= dst[0] and y + h <= dst[1]


def test_a_view_defaults_to_its_whole_size():
    v = O.View(Switches(), (320, 200))
    assert v.rect == (0, 0, 320, 200) and v.error == "" and v.handoff is None
    assert O.View(Switches(), (320, 200), viewport=(5, 6, 100, 50)).rect == (5, 6, 100, 50)
    sw = Switches()
    assert (sw.scene, sw.hands, sw.through, sw.dim) == (True, True, False, 1.0)


def test_outputs_imports_nothing_from_app_ui_or_params():
    """ARCHITECTURE §3: the render stack only reads. outputs.py imports
    moderngl and glsl at most — no app, ui, params, routing or library."""
    tree = ast.parse(Path(O.__file__).read_text())
    banned = {"app", "ui", "params", "routing", "library", "preset", "undo", "control",
              "overlay", "config"}
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.ImportFrom):
            names = [(node.module or "").split(".")[-1]] + [a.name for a in node.names]
        elif isinstance(node, ast.Import):
            names = [a.name.split(".")[-1] for a in node.names]
        assert not banned & set(names), names
        if isinstance(node, ast.ImportFrom) and node.level:
            assert node.module in (None, "glsl"), node.module


# ---------------------------------------------------------------- GL

moderngl = pytest.importorskip("moderngl")

W, H = 480, 320                 # test_ghost's size: its hand masks line up
VIEW = {"ang": [0.3, 0.7, 1.1, 0.5, 0.9, 1.3], "yaw": 0.4, "pitch": 0.25}


@pytest.fixture(scope="module")
def ctx():
    try:
        c = moderngl.create_context(standalone=True)
    except Exception as e:  # noqa: BLE001 — any GL failure means skip
        pytest.skip(f"no standalone GL context available: {e}")
    yield c
    c.release()


def _src(guide: bool = False, tmp=None):
    """Two synthetic hands (test_ghost's), with the axes for a guide."""
    from test_ghost import both, tracker

    if not guide:
        return tracker()
    from types import SimpleNamespace as NS

    from hyperspace.hands import HandSettings, HandsIO

    io = HandsIO(HandSettings.from_config({}), {}, source=NS(latest=lambda: (0, 0.0, {})),
                 out=NS(send=print))
    for st in io.state:
        st.follow.y = 0.7
    return NS(skeleton=both(), cfg={"mode": "desktop"}, axes=io.axes, state=io.state,
              gates=io.gates)


def rig(ctx, *, effects=("warp",), hands=True, bg=1.0, echoes=False, dim=1.0, guide=0,
        alpha=1.0, faces=False):
    """A renderer with `effects` on, the ghost hands on (synthetic), the
    master dim and the ground as asked."""
    from hyperspace.fx import FACES, FxState
    from hyperspace.render import Renderer

    fx = FxState()
    for n in effects:
        fx.values[n]["on"] = True
    if faces:
        fx.values["huecycle"].update(on=True, target=FACES)
    r = Renderer(ctx, fx=fx)
    r.bg_alpha, r.dim = bg, dim
    if echoes:
        st = r.lookback.state
        st.on, st.echoes, st.gap, st.tint_from = True, 8, 0.0, 0
        r.lookback.source = None
    g = r.ghost
    g.state.on, g.state.alpha, g.state.guide = hands, alpha, guide
    g.source = _src(guide=bool(guide)) if hands else None
    return r


def scene_view() -> object:
    from hyperspace.view import ViewState

    return ViewState(shape=10, ang=list(VIEW["ang"]), yaw=VIEW["yaw"], pitch=VIEW["pitch"],
                     faces=True, pattern=2)


def fbo(ctx, w=W, h=H, samples=0):
    return ctx.framebuffer(color_attachments=[ctx.renderbuffer((w, h), 4, samples=samples)])


def px(ctx, f, samples=0):
    """(h, w, 4) ints, top row first; a multisampled target resolved first."""
    import numpy as np

    w, h = f.size
    samples = samples or int(getattr(f.color_attachments[0], "samples", 0) or 0)
    if samples:
        flat = fbo(ctx, w, h)
        ctx.copy_framebuffer(flat, f)
        data = flat.read(components=4)
        f.use()                  # never release a bound framebuffer (see `today`)
        flat.release()
    else:
        data = f.read(components=4)
    return np.frombuffer(data, dtype=np.uint8).reshape(h, w, 4)[::-1].astype(int)


def views(ctx, *switches, sizes=None, bg=1.0):
    """One offscreen view per `Switches` (default size W×H)."""
    out = []
    for k, sw in enumerate(switches):
        size = (sizes or {}).get(k, (W, H))
        out.append(O.View(sw, size, target=fbo(ctx, *size), bg_alpha=bg))
    return out


def run(ctx, r, vs, frames=4, t0=2.0, spin=0.05):
    """`frames` frames of draw_outputs; each view's last picture. Every
    frame ends on the first view's target with its rect."""
    s = scene_view()
    for k in range(frames):
        s.ang = [a + spin for a in s.ang]
        r.draw_outputs(s, W, H, 1.0, vs, t_now=t0 + k / 30)
        assert ctx.fbo is vs[0].target and ctx.viewport == vs[0].rect
    assert ctx.error == "GL_NO_ERROR"
    return [px(ctx, v.target) if isinstance(v.target, moderngl.Framebuffer) else None
            for v in vs]


def today(ctx, r, frames=4, t0=2.0, spin=0.05, samples=0, size=(W, H)):
    """The same frames through `Renderer.draw` on a bound framebuffer."""
    s = scene_view()
    win = fbo(ctx, *size, samples=samples)
    for k in range(frames):
        s.ang = [a + spin for a in s.ang]
        win.use()
        ctx.viewport = (0, 0, *size)
        r.draw(s, W, H, t_now=t0 + k / 30)
        assert ctx.fbo is win
    # not released: a framebuffer released while bound makes the next
    # framebuffer made on this context raise GL_INVALID_OPERATION (moderngl
    # rebinds the old one after building the new)
    return px(ctx, win, samples)


def _parent_draw(r, s, w, h, t):
    """`Renderer.draw` as it was on the parent commit (plan 20 + WP5),
    verbatim but for `self` → `r`: the reference the default view must
    match byte for byte."""
    from hyperspace.render import _samples_of

    ctx = r.ctx
    target = ctx.fbo
    vx, vy, vw, vh = target.viewport
    vp = (vx, vy, vw, vh)
    try:
        r.scene.ensure((max(vw, 1), max(vh, 1)), _samples_of(ctx, target))
        for unit in range(4):
            r._blank.use(location=unit)
        r._pic = r._face_picture(s, t)
        try:
            r.scene.draw_fbo.use()
            ctx.viewport = (0, 0, max(vw, 1), max(vh, 1))
            r.draw_scene(s, w, h, 1.0, t)
        finally:
            r._pic = None
        r.scene.resolve()
        lb = r.lookback
        cover = r._draw_cover(w, h) if lb.wants_cover() else None
        target.viewport = (vx, vy, vw, vh)
        lb.tick(t)
        lb.pull()
        fx = r.fx
        fx.tick()
        fx.opaque = getattr(r, "bg_alpha", 1.0) >= 1.0
        if fx.active():
            buf = fx.begin(r.scene.size)
            lb.composite(r.scene.tex, buf, cover)
            lb.capture(r.scene.tex, buf)
            fx.run(target, t)
        else:
            lb.composite(r.scene.tex, target, cover)
            lb.capture(r.scene.tex, target)
        try:
            r.ghost.draw(target, vp, t, opaque=fx.opaque)
        except Exception as e:  # noqa: BLE001
            if not r.ghost.error:
                r.ghost.error = f"ghost hands: {type(e).__name__}: {e}"[:160]
            target.use()
            ctx.viewport = vp
            ctx.enable(moderngl.BLEND)
            ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        dim = getattr(r, "dim", 1.0)
        if dim < 1.0:
            r.dim_pass(target, vp, dim, opaque=fx.opaque)
    finally:
        target.use()
        ctx.viewport = (vx, vy, vw, vh)
        ctx.enable(moderngl.BLEND)


CASES = {
    "plain": {"effects": ()},
    "warp": {},
    "warp+kaleido, echoes": {"effects": ("warp", "kaleido"), "echoes": True},
    "face target": {"faces": True},
    "no hands": {"hands": False},
    "guide, dim": {"guide": 2, "dim": 0.4},
    "overlay": {"bg": 0.0, "dim": 0.6},
}


@pytest.mark.parametrize("samples", [0, 4], ids=["plain", "msaa"])
@pytest.mark.parametrize("case", list(CASES))
def test_one_default_output_is_todays_frame_byte_for_byte(ctx, case, samples):
    """`Renderer.draw` — one default view on the bound framebuffer — is the
    parent commit's frame byte for byte: effects on and off, the
    look-back, the face target, the hands off and on (with the guide), the
    dim, MSAA, an opaque ground and overlay's. Nothing is allocated for
    outputs and the one pipeline writes straight to the target. (A wider
    matrix — 320 cases with tethers — was diffed against the parent
    commit's own code while building; see the PR.)"""
    import numpy as np

    kw = CASES[case]
    ref = rig(ctx, **kw)
    s = scene_view()
    win = fbo(ctx, samples=samples)
    for k in range(4):
        s.ang = [a + 0.05 for a in s.ang]
        win.use()
        ctx.viewport = (0, 0, W, H)
        _parent_draw(ref, s, W, H, ref.now(2.0 + k / 30))
    want = px(ctx, win, samples)
    assert ctx.error == "GL_NO_ERROR"
    r = rig(ctx, **kw)
    got = today(ctx, r, samples=samples)
    assert ctx.error == "GL_NO_ERROR"
    assert want[..., :3].max() > 50
    assert np.array_equal(got, want), np.abs(got - want).max()
    assert r._frames == {} and r._show_prog is None              # nothing extra made
    assert r.stats["direct"] and r.stats["captures"] == 1
    assert r.stats["chain_runs"] == (1 if r.fx.active() else 0)


def test_the_frame_through_a_texture_is_the_same_bytes(ctx):
    """Two outputs with the same switches share one pipeline, which ends in
    a frame texture; each output's copy is the direct frame's bytes, with
    the effects on and off, at 0 and 4 samples."""
    import numpy as np

    from hyperspace.render import Renderer

    for effects in ((), ("warp",)):
        want = today(ctx, rig(ctx, effects=effects))
        r = rig(ctx, effects=effects)
        vs = views(ctx, O.Switches(), O.Switches())
        got = run(ctx, r, vs)
        assert r.stats["direct"] is False and r.stats["pipelines"] == [SCENE]
        for g in got:
            assert np.array_equal(g, want)
    # MSAA on the first output: the scene samples follow it, the copy too
    want = today(ctx, rig(ctx), samples=4)
    r = rig(ctx)
    a, b = fbo(ctx, samples=4), fbo(ctx)
    vs = [O.View(O.Switches(), (W, H), target=a), O.View(O.Switches(), (W, H), target=b)]
    run(ctx, r, vs)
    assert np.array_equal(px(ctx, a, 4), want) and np.array_equal(px(ctx, b), want)
    assert isinstance(r, Renderer)


def test_two_outputs_with_the_same_switches_run_the_chain_once(ctx):
    for sw in (O.Switches(), O.Switches(hands=False), O.Switches(scene=False)):
        r = rig(ctx)
        run(ctx, r, views(ctx, sw, O.Switches(**vars(sw))), frames=2)
        assert r.stats["chain_runs"] == (1 if sw.scene else 0), sw
        assert r.stats["captures"] == 1


@pytest.mark.parametrize("glass, projector, runs", [
    (O.Switches(), O.Switches(), 1),
    (O.Switches(), O.Switches(hands=False), 1),                  # scene + hands over / scene
    (O.Switches(), O.Switches(scene=False), 1),                  # … / hands alone, over
    (O.Switches(scene=False, hands=False), O.Switches(scene=False, hands=False), 0),
    (O.Switches(scene=False), O.Switches(scene=False), 0),
    (O.Switches(), O.Switches(through=True), 2),                 # hands over / hands through
    (O.Switches(through=True), O.Switches(scene=False, through=True), 2),   # / hands alone, through
    (O.Switches(through=True), O.Switches(through=True), 1),     # the same state: one
    (O.Switches(scene=False, through=True), O.Switches(scene=False), 1),
])
def test_outputs_that_differ_run_one_chain_per_distinct_input(ctx, glass, projector, runs):
    """The plan's table of two-output combinations: `Renderer.stats`
    counts the chain runs — at most two for two outputs, one when they
    agree."""
    r = rig(ctx)
    run(ctx, r, views(ctx, glass, projector), frames=2)
    assert r.stats["chain_runs"] == runs
    assert len(r.stats["pipelines"]) == runs
    assert r.stats["layer"] is (glass.hands or projector.hands)   # only when some output wants it
    assert r.stats["captures"] == 1


def test_the_four_scene_and_hands_states_show_their_pictures(ctx):
    """Scene on/off × hands on/off on four outputs at once: the scene with
    the hands over (today's frame); the scene alone; the hands alone on
    the ground; the ground. The hands are the same pixels over the scene
    and on the ground (they are laid over after the effects)."""
    import numpy as np
    from test_ghost import hand_mask

    S = O.Switches
    r = rig(ctx)
    both, scene, hands, black = run(ctx, r, views(
        ctx, S(), S(hands=False), S(scene=False), S(scene=False, hands=False)))
    assert np.array_equal(both, today(ctx, rig(ctx)))
    assert np.array_equal(scene, today(ctx, rig(ctx, hands=False)))
    solid = hand_mask(ctx, _src(), solid=True)
    assert solid.sum() > 500
    assert np.array_equal(hands[solid], both[solid])           # the same hands, unbent
    assert hands[~hand_mask(ctx, _src())][..., :3].max() == 0  # nothing but the hands
    assert black[..., :3].max() == 0 and black[..., 3].min() == 255
    assert r.stats["chain_runs"] == 1


def test_capture_runs_once_a_frame_whatever_the_switches(ctx, monkeypatch):
    from hyperspace.lookback import Lookback

    S = O.Switches
    calls = []
    real = Lookback.capture
    with monkeypatch.context() as m:
        m.setattr(Lookback, "capture", lambda self, *a: calls.append(1) or real(self, *a))
        for combo in ((S(),), (S(), S(hands=False), S(scene=False)),
                      (S(scene=False), S(scene=False, hands=False)), (S(), S()),
                      (S(), S(through=True), S(scene=False, through=True)),
                      (S(scene=False, through=True),)):
            for effects in ((), ("warp",)):
                calls.clear()
                run(ctx, rig(ctx, effects=effects, echoes=True), views(ctx, *combo), frames=3)
                assert len(calls) == 3, (combo, effects)


def test_the_echoes_carry_on_with_the_scene_off_everywhere(ctx):
    """No output shows the scene: the scene pass, the capture and the
    effects' clocks still run, so the history is the one a frame showing
    the scene would have, and switching the scene back on shows no gap."""
    import numpy as np

    S = O.Switches
    on = rig(ctx, echoes=True)
    off = rig(ctx, echoes=True)
    run(ctx, on, views(ctx, S()), frames=6)
    run(ctx, off, views(ctx, S(scene=False)), frames=6)
    assert off.stats["chain_runs"] == 0 and off.stats["pipelines"] == []
    assert off.lookback.layers() and off.lookback.atlas is not None
    assert np.array_equal(np.frombuffer(on.lookback.atlas.read(), dtype=np.uint8),
                          np.frombuffer(off.lookback.atlas.read(), dtype=np.uint8))
    assert on.fx.state.phase == off.fx.state.phase and off.fx.state.phase["warp"] > 0
    # the scene back on: the same frame as the renderer that never switched it off
    a = run(ctx, on, views(ctx, S()), frames=1, t0=3.0)[0]
    b = run(ctx, off, views(ctx, S()), frames=1, t0=3.0)[0]
    assert np.array_equal(a, b)


def test_the_history_never_holds_the_hands_in_any_state(ctx):
    import numpy as np

    S = O.Switches
    bare = rig(ctx, echoes=True, hands=False)
    run(ctx, bare, views(ctx, S()), frames=6)
    want = np.frombuffer(bare.lookback.atlas.read(), dtype=np.uint8)
    for combo in ((S(),), (S(), S(scene=False)), (S(scene=False),), (S(hands=False), S()),
                  (S(through=True),), (S(through=True), S(scene=False, through=True)),
                  (S(scene=False, through=True),)):
        r = rig(ctx, echoes=True)
        run(ctx, r, views(ctx, *combo), frames=6)
        assert r.stats["layer"]
        assert np.array_equal(np.frombuffer(r.lookback.atlas.read(), dtype=np.uint8), want)


def test_each_output_dims_by_master_times_its_own(ctx):
    import numpy as np

    S = O.Switches
    base = run(ctx, rig(ctx), views(ctx, S()))[0]
    a, b, c = run(ctx, rig(ctx, dim=0.5), views(ctx, S(), S(dim=0.5), S(dim=0.0)))
    assert base[..., :3].max() > 100
    assert np.abs(a[..., :3] - base[..., :3] * 0.5).max() <= 1
    assert np.abs(b[..., :3] - base[..., :3] * 0.25).max() <= 1
    assert c[..., :3].max() == 0
    for img in (a, b, c):
        assert img[..., 3].min() == 255                        # an opaque ground stays opaque
    # the master at 1, an output's own dim alone
    a, b = run(ctx, rig(ctx), views(ctx, S(), S(dim=0.3)))
    assert np.array_equal(a, base)
    assert np.abs(b[..., :3] - base[..., :3] * 0.3).max() <= 1


def test_an_output_of_another_aspect_is_letterboxed_and_the_hands_stay_registered(ctx):
    """A square output half the frame's width shows the whole frame
    centred, scaled, with black bars; the hands are laid in the same rect,
    so they sit on the same part of the shape as on the first output."""
    import numpy as np

    S = O.Switches
    r = rig(ctx)
    big, small = run(ctx, r, views(ctx, S(), S(), sizes={1: (240, 240)}))
    x, y, w, h = fit((W, H), (240, 240))
    assert (x, y, w, h) == (0, 40, 240, 160)
    bars = np.concatenate([small[:y], small[y + h:]])
    assert bars[..., :3].max() == 0 and bars[..., 3].min() == 255
    inner = small[y:y + h, x:x + w]
    half = big.reshape(h, 2, w, 2, 4).mean(axis=(1, 3))         # the frame, box-filtered
    err = np.abs(inner - half)[..., :3].mean()
    assert err < 2.0, err
    for dx, dy in ((2, 0), (0, 2)):                              # off by two pixels is far worse
        shifted = np.abs(np.roll(inner, (dy, dx), axis=(0, 1)) - half)[..., :3].mean()
        assert shifted > 3 * err + 1, (dx, dy, shifted, err)
    # the hands alone, letterboxed: they land where the frame's hands land
    hands, small_hands = run(ctx, rig(ctx), views(ctx, S(scene=False), S(scene=False),
                                                 sizes={1: (240, 240)}))
    lit_big = hands[..., :3].max(axis=2).reshape(h, 2, w, 2).max(axis=(1, 3)) > 40
    lit_small = small_hands[y:y + h, x:x + w][..., :3].max(axis=2) > 40
    assert lit_small.sum() > 200
    assert (lit_small & lit_big).sum() > 0.85 * lit_small.sum()


def test_an_opaque_grounds_alpha_is_untouched_in_every_state(ctx):
    S = O.Switches
    combos = [S(scene=a, hands=b, through=c) for a in (True, False) for b in (True, False)
              for c in (False, True)]
    for effects in ((), ("warp",), ("warp", "kaleido")):
        r = rig(ctx, effects=effects, alpha=0.6, dim=0.7)
        for img in run(ctx, r, views(ctx, *combos, S(dim=0.2), sizes={4: (300, 300)})):
            assert img[..., 3].min() == 255


def test_overlay_adds_the_hands_coverage_before_or_after(ctx):
    """Overlay's see-through ground (the first output only, in the rig):
    the hands add their coverage to the alpha whether they are laid over
    the effects or put through them; the ground with no hands stays
    see-through; the dim fades both."""
    import numpy as np
    from test_ghost import hand_mask

    S = O.Switches
    mask = hand_mask(ctx, _src(), solid=True)
    r = rig(ctx, bg=0.0)
    with_scene, alone, scene_thru, alone_thru = run(ctx, r, views(
        ctx, S(), S(scene=False), S(through=True), S(scene=False, through=True), bg=0.0))
    for img in (with_scene, alone):
        assert img[..., 3][mask].min() == 255
    outside = ~hand_mask(ctx, _src())
    assert alone[..., 3][outside].max() == 0
    assert with_scene[..., 3].min() < 255
    # through the warp the hands move a little, but their coverage comes with them
    assert alone_thru[..., 3].sum() > 0.7 * alone[..., 3].sum()
    assert scene_thru[..., 3].sum() > with_scene[..., 3].sum() - 0.3 * alone[..., 3].sum()
    for img in (scene_thru, alone_thru):                        # premultiplied: a ≥ colour
        assert (img[..., 3] + 2 >= img[..., :3].max(axis=2)).all()
    dark = alone_thru[..., :3].max(axis=2) == 0                # the ground stays see-through
    assert dark.sum() > 0.5 * dark.size and alone_thru[..., 3][dark].max() <= 2
    assert not np.array_equal(alone_thru, alone)
    faded = run(ctx, rig(ctx, bg=0.0, dim=0.5), views(ctx, S(scene=False), bg=0.0))[0]
    assert abs(faded[..., 3][mask].mean() - 127.5) <= 1


def _raiser():
    """A stand-in target whose binding raises: a view that fails."""
    from types import SimpleNamespace as NS

    def boom():
        raise RuntimeError("window gone")

    return NS(use=boom, viewport=(0, 0, W, H))


def test_the_first_target_is_bound_after_a_view_raises(ctx):
    """A view whose target raises records the error; the views after it
    are drawn, the first target is bound with its rect, the dim runs."""
    import numpy as np

    S = O.Switches
    want = run(ctx, rig(ctx, dim=0.5), views(ctx, S()))[0]
    r = rig(ctx, dim=0.5)
    vs = views(ctx, S(), S(), S())
    vs[1] = O.View(S(), (W, H), target=_raiser())
    a, _, c = run(ctx, r, vs)
    assert vs[1].error == "output: RuntimeError: window gone" and vs[0].error == vs[2].error == ""
    assert np.array_equal(a, want) and np.array_equal(c, want)


def test_a_raising_pipeline_leaves_its_views_on_the_ground_and_the_rest_drawn(ctx, monkeypatch):
    """The effect chain raises: the outputs it fed show their ground (and
    the hands over it, dimmed); an output that did not need it is drawn;
    the first target is bound; `Renderer.draw` raises it, as a frame
    always did, after the dim."""
    import numpy as np

    from hyperspace.fx import FxChain

    S = O.Switches
    want_hands = run(ctx, rig(ctx, dim=0.5), views(ctx, S(scene=False)))[0]
    r = rig(ctx, dim=0.5)
    with monkeypatch.context() as m:
        m.setattr(FxChain, "run", lambda self, *a: (_ for _ in ()).throw(RuntimeError("chain")))
        broken, hands = run(ctx, r, (vs := views(ctx, S(), S(scene=False))))
        assert vs[0].error == "SCENE: RuntimeError: chain" and vs[1].error == ""
        assert np.array_equal(broken, want_hands) and np.array_equal(hands, want_hands)
        win = fbo(ctx)
        win.use()
        ctx.viewport = (0, 0, W, H)
        with pytest.raises(RuntimeError, match="chain"):
            r.draw(scene_view(), W, H, t_now=3.0)
        assert ctx.fbo is win and ctx.viewport == (0, 0, W, H)


def test_a_raising_hands_pass_costs_no_output_its_frame_or_its_dim(ctx, monkeypatch):
    import numpy as np

    from hyperspace import ghost as G

    S = O.Switches
    want = run(ctx, rig(ctx, hands=False, dim=0.5), views(ctx, S(), S(dim=0.5)))
    for where in ("layer", "composite"):
        r = rig(ctx, dim=0.5)
        with monkeypatch.context() as m:
            if where == "layer":
                m.setattr(G.Geometry, "draw", lambda *a, **k: 1 / 0)
            else:
                m.setattr(G.Ghost, "composite", lambda *a, **k: 1 / 0)
            got = run(ctx, r, views(ctx, S(), S(dim=0.5)))
        assert r.ghost.error == "ghost hands: ZeroDivisionError: division by zero", where
        for g, w_ in zip(got, want):
            assert np.array_equal(g, w_), where


def test_the_presenter_handoff(ctx):
    """An output in another window's context gets a `Handoff`: the frame
    texture, the fit rect, the hands' layer when they go over the
    effects, ghost.alpha, master × own dim and its ground. A stand-in
    presenter (on this context, its own shaders, following the
    `Handoff` docstring step by step) shows the same picture a target
    view of the same size gets."""
    import numpy as np

    from hyperspace.glsl import QUAD_VS

    S = O.Switches
    r = rig(ctx, dim=0.8, alpha=0.7)
    first = views(ctx, S(dim=0.5))[0]
    pv = O.View(S(dim=0.5), (W, H), presenter=object())
    pv2 = O.View(S(scene=False, hands=False), (300, 300), presenter=object())
    pv3 = O.View(S(), (400, 400), presenter=object(), viewport=(10, 20, 300, 300))
    want = run(ctx, r, [first, pv, pv2, pv3])[0]
    x, y, w, h = fit((W, H), (300, 300))
    assert pv3.handoff.rect == (10 + x, 20 + y, w, h)              # inside its viewport
    ho = pv.handoff
    assert ho.frame is not None and ho.frame.size == (W, H) and ho.frame_size == (W, H)
    assert ho.rect == (0, 0, W, H) and ho.hands is r.ghost.tex and ho.readout is None
    assert ho.alpha == pytest.approx(0.7) and ho.factor == pytest.approx(0.4)
    assert ho.bg_alpha == 1.0 and O.Handoff.name(ho.frame) == ho.frame.glo
    assert pv2.handoff.frame is None and pv2.handoff.hands is None
    assert pv2.handoff.rect == fit((W, H), (300, 300))
    # the stand-in presenter: the five steps of the Handoff docstring
    show = ctx.program(vertex_shader=QUAD_VS, fragment_shader="""
        #version 330
        in vec2 v_uv; uniform sampler2D u_tex; uniform float u_k; uniform int u_opaque;
        out vec4 f;
        void main() { f = texture(u_tex, v_uv) * u_k; if (u_opaque != 0) f.a = 1.0; }""")
    dim = ctx.program(vertex_shader=QUAD_VS, fragment_shader="""
        #version 330
        uniform float u_k; out vec4 f; void main() { f = vec4(0.0, 0.0, 0.0, u_k); }""")
    vshow, vdim = ctx.vertex_array(show, []), ctx.vertex_array(dim, [])
    out = fbo(ctx)
    out.use()
    ctx.clear(0.0, 0.0, 0.0, ho.bg_alpha)                                    # 1
    ctx.viewport = ho.rect
    ctx.disable(moderngl.BLEND)
    ho.frame.use(0)
    show["u_k"].value, show["u_opaque"].value = 1.0, 1
    vshow.render(vertices=3)                                                 # 2
    ctx.enable(moderngl.BLEND)
    ctx.blend_func = moderngl.ONE, moderngl.ONE_MINUS_SRC_ALPHA, moderngl.ZERO, moderngl.ONE
    ho.hands.use(0)
    show["u_k"].value, show["u_opaque"].value = ho.alpha, 0
    vshow.render(vertices=3)                                                 # 3 (4: none)
    ctx.viewport = (0, 0, W, H)
    ctx.blend_func = moderngl.ZERO, moderngl.SRC_ALPHA, moderngl.ZERO, moderngl.ONE
    dim["u_k"].value = ho.factor
    vdim.render(vertices=3)                                                  # 5
    ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
    got = px(ctx, out)
    assert np.array_equal(got, want)
    for res in (vshow, vdim, show, dim):
        res.release()


def test_a_renderer_from_before_the_outputs_still_draws_and_reloads(ctx):
    """Hot reload: a Renderer made before plan 21 has no frame textures,
    show program or stats; draw_outputs and on_reload make them."""
    S = O.Switches
    r = rig(ctx)
    del r._frames, r._show_prog, r._show_vao, r.stats
    run(ctx, r, views(ctx, S(), S()), frames=1)
    assert r._frames and r._show_prog is not None
    r.on_reload()
    assert r._frames == {} and r._show_prog is None
    run(ctx, r, views(ctx, S(), S()), frames=1)
    assert r._frames and r.stats["pipelines"] == [SCENE]


# ---------------------------------------------------------------- WP2: hands through effects

EIGHT = [O.Switches(scene=a, hands=b, through=c)
         for a in (True, False) for b in (True, False) for c in (False, True)]


def test_each_of_the_eight_states_shows_its_picture(ctx):
    """The plan's table, warp + kaleido on, all eight on one frame:
    3 = 4 and 7 = 8 byte for byte (six pictures); 1 is today's frame and
    holds the hands undistorted; 2 and 6 differ from 1 and 5 where the
    hands are (the effects bend them); 5 is the hands alone on the
    ground; 6 is the hands alone through the chain, with no scene; 7 is
    black. Three pipelines, three chain runs, one capture."""
    import numpy as np
    from test_ghost import hand_mask

    fx = ("warp", "kaleido")
    r = rig(ctx, effects=fx)
    p = run(ctx, r, views(ctx, *EIGHT))
    assert r.stats["pipelines"] == [SCENE, SCENE_HANDS, HANDS]
    assert r.stats["chain_runs"] == 3 and r.stats["captures"] == 1
    s1, s2, s3, s4, s5, s6, s7, s8 = p
    assert np.array_equal(s3, s4) and np.array_equal(s7, s8)
    assert len({a.tobytes() for a in p}) == 6
    assert np.array_equal(s1, today(ctx, rig(ctx, effects=fx)))          # the default
    solid, cover = hand_mask(ctx, _src(), solid=True), hand_mask(ctx, _src())
    assert np.array_equal(s1[solid], s5[solid])                         # unbent, over the scene
    assert s5[~cover][..., :3].max() == 0                               # the hands alone
    for through, over in ((s2, s1), (s6, s5)):
        assert np.abs(through[cover] - over[cover])[..., :3].sum() > 50_000
    assert s6[..., :3].max() > 100 and s6[..., 3].min() == 255          # hands, bent, on black
    assert s7[..., :3].max() == 0
    # the scene through the effects is the same in 1, 2 and 3 away from the hands
    # (2: up to rounding where a bent hand's faint edge lands)
    far = ~cover & ~(s6[..., :3].max(axis=2) > 0)
    assert np.array_equal(s1[far], s3[far])
    assert np.abs(s2[far] - s3[far]).mean() < 0.5


def test_two_pipelines_show_the_same_echoes(ctx):
    """Echoes on, one output with the hands over and one with them
    through: both composite the history as it was before this frame's
    capture, so away from the hands the two scenes are the same picture
    (review of PR #120: a capture between the two composites gave the
    second a doubled current frame and echoes a frame older)."""
    import numpy as np
    from test_ghost import hand_mask

    S = O.Switches
    r = rig(ctx, effects=("warp",), echoes=True)
    over, through, alone = run(ctx, r, views(ctx, S(), S(through=True),
                                             S(scene=False, through=True)), frames=8)
    assert r.lookback.layers() and r.stats["captures"] == 1
    far = ~hand_mask(ctx, _src()) & ~(alone[..., :3].max(axis=2) > 0)
    assert np.abs(through[far] - over[far]).mean() < 0.5
    bare = run(ctx, rig(ctx, effects=("warp",), echoes=True, hands=False), views(ctx, S()),
               frames=8)[0]
    assert np.array_equal(over[far], bare[far])


def test_through_bends_the_hands_with_the_shape(ctx):
    """Under the warp alone, the hands through the effects are not where
    the hands over them are: the pixels moved — while over the effects
    they are exactly where the hands' own pass puts them."""
    import numpy as np
    from test_ghost import hand_mask

    S = O.Switches
    over, through = run(ctx, rig(ctx), views(ctx, S(scene=False), S(scene=False, through=True)))
    lit_o = over[..., :3].max(axis=2) > 40
    lit_t = through[..., :3].max(axis=2) > 40
    assert np.array_equal(lit_o, hand_mask(ctx, _src()) & lit_o)
    moved = (lit_o ^ lit_t).sum()
    assert moved > 0.2 * lit_o.sum(), (moved, lit_o.sum())


def test_through_with_no_effect_on_is_hands_over(ctx):
    import numpy as np

    S = O.Switches
    r = rig(ctx, effects=())
    a, b, c, d = run(ctx, r, views(ctx, S(), S(through=True), S(scene=False),
                                   S(scene=False, through=True)))
    assert np.array_equal(a, b) and np.array_equal(c, d)
    assert r.stats["pipelines"] == [SCENE] and r.stats["chain_runs"] == 0
    assert r.stats["readout"] is False


def test_through_with_no_hand_showing_runs_nothing_extra(ctx):
    import numpy as np

    S = O.Switches
    for src in ("off", "no hand", "hands switch off"):
        r = rig(ctx)
        sw = [S(), S(through=True)]
        if src == "off":
            r.ghost.state.on = False
        elif src == "no hand":
            r.ghost.source.skeleton = {}
        else:
            sw = [S(hands=False), S(hands=False, through=True)]
        a, b = run(ctx, r, views(ctx, *sw))
        assert np.array_equal(a, b), src
        assert r.stats["pipelines"] == [SCENE] and r.stats["chain_runs"] == 1, src
        assert r.ghost.readout is None and r._frames.keys() == {SCENE}, src


def test_four_outputs_need_at_most_three_chain_runs(ctx):
    S = O.Switches
    r = rig(ctx)
    run(ctx, r, views(ctx, S(), S(through=True), S(scene=False, through=True), S(hands=False)),
        frames=2)
    assert r.stats["chain_runs"] == 3 and r.stats["pipelines"] == [SCENE, SCENE_HANDS, HANDS]


def _readout_alpha(r):
    import numpy as np

    tex = r.ghost.readout
    w, h = tex.size
    return np.frombuffer(tex.read(), dtype=np.uint8).reshape(h, w, 4)[::-1, :, 3]


@pytest.mark.parametrize("guide", [1, 2], ids=["beside", "on hand"])
def test_the_guide_is_never_distorted(ctx, guide):
    """Fork F3: with a pipeline putting the hands through the effects and
    the guide on, the guide is a layer of its own (`Ghost.readout`) laid
    over after everything on every output that shows the hands: where it
    is solid, the output with the hands through the effects shows the
    same pixels as the one with them over — and as today's single-layer
    frame. Not needed (no through, or no guide), it is not drawn and the
    frame is today's, byte for byte."""
    import numpy as np

    S = O.Switches
    fx = ("warp", "kaleido")
    r = rig(ctx, effects=fx, guide=guide)
    over, through, alone = run(ctx, r, views(ctx, S(), S(through=True),
                                             S(scene=False, through=True)))
    assert r.stats["readout"] is True and r.ghost.readout is not None
    solid = _readout_alpha(r) == 255
    assert solid.sum() > 150
    for img in (through, alone):
        assert np.array_equal(img[solid], over[solid])
    single = today(ctx, rig(ctx, effects=fx, guide=guide))         # the guide in the hands' layer
    assert np.array_equal(over[solid], single[solid])
    # not needed: no through pipeline — today's frame, no readout drawn
    r2 = rig(ctx, effects=fx, guide=guide)
    a, b = run(ctx, r2, views(ctx, S(), S(scene=False)))
    assert r2.ghost.readout is None and r2.stats["readout"] is False
    assert np.array_equal(a, single)
    # …or no guide
    r3 = rig(ctx, effects=fx)
    run(ctx, r3, views(ctx, S(), S(through=True)))
    assert r3.ghost.readout is None and r3.stats["readout"] is False
    # …or no effect on: through is over, and the readout is not split
    r4 = rig(ctx, effects=(), guide=guide)
    a, b = run(ctx, r4, views(ctx, S(), S(through=True)))
    assert r4.ghost.readout is None and np.array_equal(a, b)


def test_a_raising_hands_composite_into_the_chain_still_runs_it(ctx, monkeypatch):
    """The hands raising as they go onto the chain's input: that output
    shows the scene through the effects with no hands, dimmed; the other
    outputs are drawn; `Ghost.error` says why."""
    import numpy as np

    from hyperspace import ghost as G

    S = O.Switches
    want = run(ctx, rig(ctx, hands=False, dim=0.5), views(ctx, S()))[0]
    r = rig(ctx, dim=0.5)
    real = G.Ghost._lay
    with monkeypatch.context() as m:
        def boom(self, tex, target, vp, opaque):
            if tuple(vp[:2]) == (0, 0) and target is r.fx._fbo[0]:
                raise RuntimeError("into the chain")
            return real(self, tex, target, vp, opaque)
        m.setattr(G.Ghost, "_lay", boom)
        through, over = run(ctx, r, views(ctx, S(through=True), S()))
    assert r.ghost.error == "ghost hands: RuntimeError: into the chain"
    assert np.array_equal(through, want)
    assert not np.array_equal(over, want)                          # the hands, over
    assert through[..., 3].min() == 255


def test_the_presenter_handoff_carries_the_readout(ctx):
    S = O.Switches
    r = rig(ctx, guide=1)
    first = views(ctx, S(through=True))[0]
    pv = O.View(S(), (W, H), presenter=object())
    pv_off = O.View(S(hands=False), (W, H), presenter=object())
    run(ctx, r, [first, pv, pv_off])
    assert pv.handoff.readout is r.ghost.readout is not None
    assert pv.handoff.hands is r.ghost.tex
    assert pv_off.handoff.readout is None and pv_off.handoff.hands is None
    assert r.stats["chain_runs"] == 2 and r.stats["direct"] is False


@pytest.mark.parametrize("style", range(1, 5))
def test_every_style_behaves_as_the_hands_in_every_state(ctx, style):
    """Plan 21 WP6: a style is drawn into the same hands' layer, so the
    eight states hold for it as for HANDS — 3 = 4 and 7 = 8, six pictures,
    the style alone on the ground in 5, bent by the effects in 2 and 6 —
    and with the guide on and a through pipeline the guide is the readout
    layer, unbent: the same pixels over and through."""
    import numpy as np

    from hyperspace import ghost as G

    fx = ("warp", "kaleido")
    r = rig(ctx, effects=fx, guide=1)
    r.ghost.state.style = style
    p = run(ctx, r, views(ctx, *EIGHT))
    s1, s2, s3, s4, s5, s6, s7, s8 = p
    assert np.array_equal(s3, s4) and np.array_equal(s7, s8), G.STYLES[style]
    assert len({a.tobytes() for a in p}) == 6
    assert s5[..., :3].max() > 100 and s7[..., :3].max() == 0
    cover = s5[..., :3].max(axis=2) > 0
    assert np.abs(s6[cover] - s5[cover])[..., :3].sum() > 20_000      # bent
    solid = _readout_alpha(r) == 255
    assert solid.sum() > 150
    for through, over in ((s2, s1), (s6, s5)):
        assert np.array_equal(through[solid], over[solid])


# ---------------------------------------------------------------- WP3: the presenter

def _presented(ctx, r, pairs, frames=4):
    """Each (switches, size) twice in one frame: a target view and a
    presenter view. The presenter (outputs.Presenter, on this context:
    a stand-in for another window's, which shares textures by GL name)
    shows its handoff into a framebuffer of that size. Returns
    [(target picture, presented picture)]."""
    pres = O.Presenter(ctx)
    vs = [O.View(O.Switches(), (W, H), target=fbo(ctx))]
    for sw, size in pairs:
        vs.append(O.View(sw, size, target=fbo(ctx, *size)))
        vs.append(O.View(sw, size, presenter=pres))
    run(ctx, r, vs, frames=frames)
    out = []
    for i in range(len(pairs)):
        tv, pv = vs[1 + 2 * i], vs[2 + 2 * i]
        dst = fbo(ctx, *pv.size)
        pres.present(pv.handoff, pv.size, target=dst)
        assert ctx.fbo is dst and ctx.viewport == (0, 0, *pv.size)    # left bound
        out.append((px(ctx, tv.target), px(ctx, dst)))
    vs[0].target.use()
    pres.release()
    return out


@pytest.mark.parametrize("effects", [(), ("warp", "kaleido")])
def test_the_presenter_shows_what_a_target_view_shows(ctx, effects):
    """WP3's presenter follows the `Handoff`'s five steps with its own
    programs: for every switch state, at the frame's size and letterboxed
    into another shape, with ghost.alpha, the guide's readout layer and
    master × own dim, its picture is the target view's, byte for byte."""
    import numpy as np

    S = O.Switches
    r = rig(ctx, effects=effects, alpha=0.7, dim=0.8, guide=1)
    pairs = [(sw, (W, H)) for sw in EIGHT]
    pairs += [(S(dim=0.5), (300, 300)), (S(through=True, dim=0.6), (W, H)),
              (S(scene=False), (640, 300))]
    got = _presented(ctx, r, pairs)
    for (sw, size), (want, shown) in zip(pairs, got, strict=True):
        assert np.array_equal(want, shown), (sw, size)
        assert shown[..., 3].min() == 255                    # a later output is opaque
    assert any(p[0][..., :3].max() > 100 for p in got)       # something was drawn


def test_the_presenter_rebuilds_after_a_reload_in_its_own_context(ctx):
    """`on_reload` touches no GL (a reload runs in whatever context is
    current); the next `present` rebuilds the programs, and the picture
    is the same."""
    import numpy as np

    r = rig(ctx)
    pres = O.Presenter(ctx)
    assert pres._prog is None                               # nothing built before a present
    pv = O.View(O.Switches(), (W, H), presenter=pres)
    run(ctx, r, [O.View(O.Switches(), (W, H), target=fbo(ctx)), pv], frames=2)
    a, b = fbo(ctx), fbo(ctx)
    pres.present(pv.handoff, pv.size, target=a)
    old = pres._prog
    pres.on_reload()
    assert pres._prog is old                                # marked, not released
    pres.present(pv.handoff, pv.size, target=b)
    assert pres._prog is not old and np.array_equal(px(ctx, a), px(ctx, b))
    pres.release()
    assert pres._prog is None and pres._ext == {}


def test_a_capped_frame_is_drawn_smaller_and_shown_whole_on_output_one(ctx):
    """The render cap (output.render): output 1 a 2× HiDPI framebuffer
    (2W×2H at dpr 2) under a W×H cap draws the scene at W×H — the strokes
    at their on-screen width, dpr scaled alike — and shows it scaled over
    the whole framebuffer: box-filtered back down it is the uncapped W×H
    frame at dpr 1."""
    import numpy as np

    S = O.Switches
    ref = run(ctx, rig(ctx), views(ctx, S()))[0]
    r = rig(ctx)
    r.max_frame = (W, H)
    vs = views(ctx, S(), sizes={0: (2 * W, 2 * H)})
    s = scene_view()
    for k in range(4):
        s.ang = [a + 0.05 for a in s.ang]
        r.draw_outputs(s, W, H, 2.0, vs, t_now=2.0 + k / 30)
    assert ctx.error == "GL_NO_ERROR"
    assert r.scene.size == (W, H) and r.stats["direct"] is False
    big = px(ctx, vs[0].target)
    assert big.shape == (2 * H, 2 * W, 4)
    down = big.reshape(H, 2, W, 2, 4).mean(axis=(1, 3))
    err = np.abs(down - ref)[..., :3].mean()
    assert err < 3.0, err
    # uncapped, the same framebuffer draws at its own size, direct
    r.max_frame = None
    r.draw_outputs(s, W, H, 2.0, vs, t_now=3.0)
    assert r.scene.size == (2 * W, 2 * H) and r.stats["direct"] is True
