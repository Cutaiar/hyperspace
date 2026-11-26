"""WP6a — the look-back core: history ring, age-weighted composite, the
dream slot's copy path, the dream.* params and their loadable patches, the page.

Everything runs offscreen on a standalone GL context (skipped where there
is none). The composite is checked against a numpy transcription of the
shader's math at the echo's own size, so sampling is one-to-one and the
only tolerance is 8-bit rounding.
"""

from __future__ import annotations

import json
import time
from types import SimpleNamespace

import numpy as np
import pytest
from conftest import CORPUS, seed

moderngl = pytest.importorskip("moderngl")

from hyperspace.lookback import (
    RES,
    DreamState,
    LookbackSource,
    echo_size,
)
from hyperspace.overlay import Output
from hyperspace.render import Renderer
from hyperspace.view import ViewState

VIEW = {"ang": [0.3, 0.7, 1.1, 0.5, 0.9, 1.3], "yaw": 0.4, "pitch": 0.25}


class Rig:
    """A renderer on an RGBA texture target of size (w, h), read back as arrays."""

    def __init__(self, ctx, w, h, bg_alpha=1.0, dream=None):
        self.ctx, self.w, self.h = ctx, w, h
        self.tex = ctx.texture((w, h), 4)
        self.fbo = ctx.framebuffer(color_attachments=[self.tex])
        self.r = Renderer(ctx, dream)
        self.r.bg_alpha = bg_alpha
        self.lb = self.r.dreamer
        self.s = ViewState(shape=3, ang=list(VIEW["ang"]), yaw=VIEW["yaw"], pitch=VIEW["pitch"])

    def frame(self, t=0.0):
        self.fbo.use()
        self.ctx.viewport = (0, 0, self.w, self.h)
        self.r.draw(self.s, self.w, self.h, t_now=t)
        self.s.ang[3] += 0.03

    def read(self):
        return np.frombuffer(self.fbo.read(components=4), dtype=np.uint8).reshape(
            self.h, self.w, 4).copy()

    def scene(self):
        """The scene texture as the post pass sees it."""
        return np.frombuffer(self.r.scene.fbo.read(components=4), dtype=np.uint8).reshape(
            self.h, self.w, 4).copy()

    def release(self):
        self.fbo.release()
        self.tex.release()


# ---------------------------------------------------------------- the ring

def test_echo_size_keeps_aspect():
    assert echo_size(256, 1280, 820) == (400, 256)
    assert echo_size(256, 820, 1280) == (256, 400)
    assert echo_size(128, 1920, 1080) == (224, 128)
    assert echo_size(256, 256, 256) == (256, 256)


# ---------------------------------------------------------------- the composite

def grade(c, contrast, darken):
    return np.power(np.maximum(c, 1e-6), contrast) * (1.0 - darken)


def reference(scene, layers, darken, contrast, occlude=1.0):
    """The shader's math in numpy: scene (h, w, 4) float, layers [(rgba, w)]
    oldest first; returns (h, w, 4) float."""
    wake = np.zeros(scene.shape[:2] + (3,), dtype=np.float64)
    wa = np.zeros(scene.shape[:2], dtype=np.float64)
    for rgba, w in layers:
        c = grade(rgba[..., :3], contrast, darken)
        a = w * c.max(axis=2)
        wake = wake * (1.0 - a)[..., None] + c * w
        wa = wa + a - wa * a
    cover = occlude * np.minimum(scene[..., :3].max(axis=2) * 4.0, 1.0)
    wake = wake * (1.0 - cover)[..., None]
    wa = wa * (1.0 - cover)
    out = np.empty_like(scene)
    out[..., :3] = np.minimum(scene[..., :3] + wake, 1.0)
    out[..., 3] = scene[..., 3] + wa - scene[..., 3] * wa
    return out


def synthetic(h, w, seed):
    """A smooth, coloured test image with black ground on one side."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    img = np.zeros((h, w, 4), dtype=np.float64)
    for ch in range(3):
        f = rng.uniform(0.02, 0.08, 2)
        img[..., ch] = 0.5 + 0.5 * np.sin(xx * f[0] + yy * f[1] + rng.uniform(0, 6))
    img[:, : w // 4] = 0.0          # a black quarter: covers nothing
    img[..., 3] = 1.0
    return (img * 255).round().astype(np.uint8)


LUMA = np.array([0.299, 0.587, 0.114])


def rotate_hue(c, degrees):
    """The shader's YIQ rotation: the chroma plane turned, luma kept."""
    a = np.radians(degrees)
    y = c @ LUMA
    i = c @ np.array([0.596, -0.274, -0.322])
    q = c @ np.array([0.211, -0.523, 0.312])
    i2, q2 = i * np.cos(a) - q * np.sin(a), i * np.sin(a) + q * np.cos(a)
    return np.stack([y + 0.956 * i2 + 0.621 * q2, y - 0.272 * i2 - 0.647 * q2,
                     y - 1.106 * i2 + 1.703 * q2], axis=-1)


def chroma(c, hue, sat, tint, tint_rgb):
    """The shader's chroma stage in numpy on an (h, w, 3) float image."""
    lum = (c @ LUMA)[..., None]
    own = lum + (rotate_hue(c, hue) - lum) * sat
    return np.clip(own * (1.0 - tint) + lum * np.asarray(tint_rgb) * tint, 0.0, 1.0)


def scene_hue_tint(scene, sat):
    """The tint colour the shader takes from the scene: the hue of its
    mean colour at `sat`, full value — grey when the mean has no chroma."""
    import colorsys

    m = scene[..., :3].reshape(-1, 3).mean(axis=0)
    if m.max() - m.min() < 1e-4:
        return (1.0, 1.0, 1.0)
    h, _, _ = colorsys.rgb_to_hsv(*m)
    return colorsys.hsv_to_rgb(h, sat, 1.0)


def dream_over(under, coloured, mix, darken, contrast):
    """The dream pass in numpy (plan 36 T4, DREAM_FS): `coloured` graded and
    laid premultiplied over `under` at `mix`, its luminance its coverage."""
    c = grade(coloured, contrast, darken)
    a = mix * c.max(axis=2)
    out = np.empty_like(under)
    out[..., :3] = under[..., :3] * (1.0 - a)[..., None] + c * mix
    out[..., 3] = under[..., 3] + a - under[..., 3] * a
    return out


@pytest.mark.parametrize("chroma_kw, tint_rgb", [
    # the net's own colours re-hued and half desaturated, no tint
    ({"hue": 120.0, "sat": 0.5, "tint": 0.0}, None),
    # pushed past the net's saturation, hue the other way, a touch of tint
    ({"hue": -70.0, "sat": 1.6, "tint": 0.3, "tint_hue": 30.0, "tint_sat": 0.8}, None),
    # fully tinted to one colour: luminance × green
    ({"tint": 1.0, "tint_from": 0, "tint_hue": 120.0, "tint_sat": 1.0}, (0.0, 1.0, 0.0)),
    # greyscale: fully tinted, the tint itself grey
    ({"sat": 0.0, "tint": 1.0, "tint_sat": 0.0}, (1.0, 1.0, 1.0)),
    # the scene's own hue
    ({"tint": 1.0, "tint_from": 1, "tint_sat": 0.85}, "scene"),
])
def test_dream_chroma_matches_numpy_reference(ctx, chroma_kw, tint_rgb):
    """The chroma stage on the dream buffer (plan 36 T4: the dream node's
    pass, `Dreamer.lay`, over its picture): the shader against the numpy
    transcription, tint colour included — the chosen one, or the hue of
    its input's mean, read off the submit."""
    import colorsys

    w, h = echo_size(128, 400, 256)
    state = DreamState(on=True, res=0, darken=0.2, contrast=1.3, mix=0.6, **chroma_kw)
    rig = Rig(ctx, w, h, dream=state)
    rig.frame()
    lb = rig.r.dreamer
    # a picture with a decided colour cast, submitted as the dream node
    # would (at the submit size here, so the downsample is one to one)
    scene8 = synthetic(h, w, 21)
    scene8[..., :3] = (scene8[..., :3] * np.array([0.25, 0.55, 1.0])).round().astype(np.uint8)
    rig.r.scene.tex.write(scene8)
    lb.submit(rig.r.scene.tex, w, h)
    dream8 = synthetic(h, w, 9)
    lb._ensure(w, h)
    lb.write_from(dream8, frame_index=lb.frame)
    rig.fbo.use()
    ctx.viewport = (0, 0, w, h)
    lb.lay(rig.r.scene.tex, rig.fbo)
    out = rig.read().astype(np.float64) / 255.0
    scene = scene8.astype(np.float64) / 255.0
    dream = dream8.astype(np.float64)[..., :3] / 255.0
    if tint_rgb == "scene":
        from hyperspace.lookback import mean_colour, scene_tint

        # the composite's colour is off the strided mean of the echo, which
        # sits on the exact mean's hue to within a degree or so
        exact = scene_hue_tint(scene, state.tint_sat)
        assert max(exact) - min(exact) > 0.5, "the cast must give a real hue"
        assert lb.input_mean == pytest.approx(mean_colour(scene8), abs=1e-6)
        assert lb.input_mean == pytest.approx(scene[..., :3].reshape(-1, 3).mean(axis=0),
                                              abs=0.01)
        tint_rgb = lb.tint_rgb()
        assert tint_rgb == pytest.approx(scene_tint(mean_colour(scene8), state.tint_sat))
        assert tint_rgb == pytest.approx(exact, abs=0.03)
    elif tint_rgb is None:
        tint_rgb = colorsys.hsv_to_rgb(state.tint_hue / 360.0, state.tint_sat, 1.0)
        assert lb.input_mean is None, "colour mode never reads the input back"
    coloured = chroma(dream, state.hue, state.sat, state.tint, tint_rgb)
    ref = dream_over(scene, coloured, 0.6, 0.2, 1.3)
    err = np.abs(out - ref)
    assert err.max() <= 2.5 / 255, f"max error {err.max() * 255:.2f}/255"
    assert err.mean() <= 0.4 / 255
    assert np.abs(out - scene).mean() > 0.02, "the dream is really there"
    # the black quarter of the dream adds nothing whatever its chroma
    assert np.array_equal((out[:, : w // 4] * 255).round(), (scene[:, : w // 4] * 255).round())
    rig.release()


def test_dream_chroma_is_neutral_by_default(ctx):
    """Fresh state: hue 0, sat 1, tint 0 leaves the dream as the net painted it."""
    w, h = echo_size(128, 400, 256)
    d = DreamState(on=True, res=0, darken=0.0, contrast=1.0, mix=1.0)
    assert (d.hue, d.sat, d.tint) == (0.0, 1.0, 0.0)
    rig = Rig(ctx, w, h, dream=d)
    rig.frame()
    dream8 = synthetic(h, w, 9)
    dr = rig.r.dreamer
    dr._ensure(w, h)
    dr.write_from(dream8, frame_index=1)
    rig.r.scene.tex.write(np.zeros((h, w, 4), dtype=np.uint8))     # a black picture
    rig.fbo.use()
    ctx.viewport = (0, 0, w, h)
    dr.lay(rig.r.scene.tex, rig.fbo)
    out = rig.read().astype(int)
    # weight 1 over black: the composite is the dream itself (8-bit rounding)
    assert np.abs(out[..., :3] - dream8.astype(int)[..., :3]).max() <= 1
    rig.release()


def test_tint_colour():
    from hyperspace.lookback import TINT_FROM, mean_colour, scene_tint, tint_colour

    assert TINT_FROM == ["colour", "scene"]
    assert tint_colour(0.0, 1.0) == pytest.approx((1.0, 0.0, 0.0))
    assert tint_colour(120.0, 1.0) == pytest.approx((0.0, 1.0, 0.0))
    assert tint_colour(480.0, 1.0) == pytest.approx((0.0, 1.0, 0.0))   # wraps
    assert tint_colour(200.0, 0.0) == pytest.approx((1.0, 1.0, 1.0))   # grey
    assert tint_colour(240.0, 0.5) == pytest.approx((0.5, 0.5, 1.0))
    # from a scene: its hue, the chosen saturation, full value
    assert scene_tint((0.1, 0.1, 0.4), 1.0) == pytest.approx((0.0, 0.0, 1.0))
    assert scene_tint((0.3, 0.2, 0.2), 0.5) == pytest.approx((1.0, 0.5, 0.5))
    assert scene_tint((0.2, 0.2, 0.2), 1.0) == (1.0, 1.0, 1.0)         # no chroma: grey
    assert scene_tint(None, 1.0) == (1.0, 1.0, 1.0)                    # nothing captured
    # the mean samples a stride grid: 8 rows × 12 columns → 2 × 3 samples
    img = np.zeros((8, 12, 4), dtype=np.uint8)
    img[..., 0], img[..., 2], img[..., 3] = 255, 51, 255
    img[:4, :, 0] = 0                    # half the rows red-less: mean r 0.5
    assert mean_colour(img) == pytest.approx((0.5, 0.0, 0.2), abs=1e-6)
    img[1::2, :, 1] = 255                # off the grid: not seen
    assert mean_colour(img) == pytest.approx((0.5, 0.0, 0.2), abs=1e-6)


def test_scene_tint_reads_the_echo_only_when_asked(ctx):
    """A tint from the dream's input costs one read-back a frame; colour
    mode never reads. With a source attached the worker's own read serves
    both. The dream off clears the mean (plan 36 T4: the dream node's own
    read of its input, no look-back's)."""
    w, h = echo_size(128, 400, 256)
    d = DreamState(on=True, res=0, tint_from=1)
    rig = Rig(ctx, w, h, dream=d)
    lb = rig.r.dreamer
    for _ in range(4):
        rig.frame()
    assert lb.input_mean is not None and lb.frame == 4
    mean = lb.input_mean
    d.tint_from = 0
    lb.input_mean = None
    for _ in range(3):
        rig.frame()
    assert lb.input_mean is None and lb.frame == 4
    d.tint_from = 1
    src = Echo()
    lb.source = src
    n = src.buffers
    rig.frame()
    assert src.buffers == n + 1 and lb.input_mean is not None
    assert lb.input_mean == pytest.approx(mean, abs=0.05)   # the same picture, near enough
    d.on = False
    rig.frame()
    assert lb.input_mean is None
    rig.release()


def test_composite_is_a_copy_when_nothing_is_layered(ctx):
    rig = Rig(ctx, 200, 128, dream=DreamState(on=True, res=0))
    rig.frame()
    rig.frame()
    assert np.array_equal(rig.read(), rig.scene())
    rig.release()


def test_cut_through_never_cuts_an_opaque_ground(ctx):
    """Plan 14 WP1 (the Pepper's Ghost rig): on an opaque ground — window
    and fullscreen — faces leave every pixel at alpha 255 whether
    cut-through is on (the default) or off; the fills still draw."""
    rig = Rig(ctx, 256, 256, bg_alpha=Output(None, None).bg_alpha)   # window mode: 1
    rig.s.faces, rig.s.lines, rig.s.points = True, True, False
    assert rig.s.cut_through
    for cut in (True, False):
        rig.s.cut_through = cut
        rig.frame()
        out = rig.read()
        assert (out[..., 3] == 255).all(), f"cut_through={cut} let the desktop through"
        assert out[..., :3].max() > 0, "the fills must still draw"
    rig.release()


def test_cut_through_still_cuts_in_overlay_mode(ctx):
    """Overlay mode's see-through ground: cut-through on lets the fills
    lower the window's alpha below the ground's; off, alpha composites over
    the ground and never drops below it."""
    out_ = Output(None, None, allowed=True)   # [output] overlay = true
    out_.overlay, out_.bg = True, 0.6
    rig = Rig(ctx, 256, 256, bg_alpha=out_.bg_alpha)
    ground = round(0.6 * 255)
    rig.s.faces, rig.s.lines, rig.s.points = True, False, False
    rig.s.cut_through = True
    rig.frame()
    assert rig.read()[..., 3].min() < ground - 2, "in overlay the fills must cut the alpha"
    rig.s.cut_through = False
    rig.frame()
    out = rig.read()
    assert out[..., 3].min() >= ground - 1
    assert out[..., :3].max() > 0
    rig.release()


def _preset_rig(ctx, tmp_path):
    """The app's construction order (tests/test_loadable.py `boot`), the
    renderer's own dream and fx states on the registry."""
    from hyperspace import lfo, tempo
    from hyperspace.analysis import Analyser
    from hyperspace.analyzer import Analyzer
    from hyperspace.control import Control
    from hyperspace.library import Library
    from hyperspace.loadable import LoadedPatch
    from hyperspace.params import build_registry
    from hyperspace.routing import Bindings, Router

    chain = Analyzer(Analyser())
    control = Control(chain)
    view = ViewState()
    r = Renderer(ctx)
    seed(tmp_path)                   # (the corpus: the loadable patches the build once shipped)
    lib = Library(tmp_path, period=0.0)
    reg = build_registry(view, control, SimpleNamespace(chain=chain), lib.install,
                         dream=r.lookback.state, fx=r.fx.state)
    control.library = lib
    clock = tempo.Clock(now=lambda: 0.0)
    tempo.register(reg, clock)
    lfo.register(reg, lfo.LFOs(), clock)
    lib.attach(reg)
    router = Router(reg, Bindings())
    loaded_patch = LoadedPatch(lib, reg, router)
    return SimpleNamespace(lib=lib, reg=reg, view=view, r=r, loaded_patch=loaded_patch)


def _final_alpha(ctx, b, bg_alpha, w=240, h=160, frames=4):
    tex = ctx.texture((w, h), 4)
    fbo = ctx.framebuffer(color_attachments=[tex])
    b.r.bg_alpha = bg_alpha
    for k in range(frames):
        b.reg.apply()
        b.view.integrate(1 / 60)
        fbo.use()
        ctx.viewport = (0, 0, w, h)
        b.r.draw(b.view, w, h, t_now=k / 60)
    a = np.frombuffer(fbo.read(components=4), dtype=np.uint8).reshape(h, w, 4)[..., 3].copy()
    fbo.release()
    tex.release()
    return a


def _corpus_loadables():
    """The loadable patches the build once shipped (tests/corpus/loadable), by slug."""
    return sorted(p.stem for p in (CORPUS / "loadable").glob("*.json"))


# every effect on at its own blend, then every one forced to multiply
# (a × b drops alpha wherever an effect returns less than 1)
STRESS = ["effects", "multiply"]


@pytest.mark.parametrize("name", _corpus_loadables() + STRESS)
def test_every_corpus_loadable_renders_opaque_in_window_mode(ctx, tmp_path, name):
    """Plan 14 WP1: the render window is a Pepper's Ghost screen — in window
    mode (and fullscreen, the same opaque ground) every pixel of the final
    frame is alpha 255 for every corpus loadable patch, and for a loadable patch with
    cut-through, faces, points, the look-back and every effect on, through
    the FX chain and the look-back composite."""
    b = _preset_rig(ctx, tmp_path)
    first = _corpus_loadables()[0] if name in STRESS else name
    path = b.lib.path_of("loadable", first)
    assert path is not None, first
    b.loaded_patch.load(json.loads(path.read_text())["name"])
    assert b.lib.current("loadable") is not None
    if name in STRESS:
        # (plan 36 T3: every effect file exists for the stress, as before a
        # graph landed — `FxState.hold(None)`)
        from hyperspace.fx import declare

        declare(b.reg, b.r.fx.state, b.r.fx.state.hold(None))
        values = {"view.faces": True, "view.cut_through": True, "view.lines": True,
                  "view.points": True, "fx.on": True, "fx.mix": 1.0, "dream.on": True,
                  "dream.echoes": 6, "dream.gap": 0.0}
        for fx_name in b.r.fx.state.specs:
            values[f"fx.{fx_name}.on"] = True
            values[f"fx.{fx_name}.mix"] = 1.0
        assert b.reg.restore(values) == []
        # plan 33 R23: every effect in the run, as a load of these values lands it
        from hyperspace.graphmigrate import wiring_of
        b.r.wiring = wiring_of(b.r.fx.state)
        if name == "multiply":
            for fx_name in b.r.fx.state.specs:
                b.reg[f"fx.{fx_name}.blend"].set(3)
    a = _final_alpha(ctx, b, Output(None, None).bg_alpha)
    assert (a == 255).all(), f"{name}: {(a < 255).mean():.1%} below 255, lowest {a.min()}"
    if name in STRESS:
        assert b.r.stats["fx_on"] and b.view.cut_through and b.view.faces


# ---------------------------------------------------------------- the dream slot

class Echo:
    """A source that answers every submit with the frame it was given,
    tagged, one call late — enough to prove the hand-off both ways."""

    def __init__(self):
        self.pending = None
        self.done = None
        self.submitted = []
        self.buffers = 0

    def buffer(self, shape):
        self.buffers += 1
        return np.empty(shape, dtype=np.uint8)

    def submit(self, frame, frame_index):
        self.submitted.append((frame, frame_index))
        self.done = self.pending
        self.pending = (frame.copy(), frame_index)

    def latest(self):
        return self.done


def test_source_protocol():
    assert isinstance(Echo(), LookbackSource)
    assert not isinstance(object(), LookbackSource)


def test_dream_slot_round_trip(ctx):
    """Plan 36 T4: the dream node submits its own input (the scene, laid
    over it: plan 90 H2 — the look-back it dreamed in an old dream preset's
    frame is retired) and pulls its own results."""
    w, h = echo_size(128, 400, 256)
    src = Echo()
    rig = Rig(ctx, w, h, dream=DreamState(on=True, res=0, mix=1.0, darken=0.0))
    dr = rig.r.dreamer
    dr.source = src
    rig.frame()
    frame1, idx = src.submitted[-1]
    assert idx == 1 and frame1.shape == (h, w, 4) and src.buffers == 1
    # nothing answered yet: the dream passes its picture through
    assert dr.dream_frame == -1
    rig.frame()            # submit 2; answers submit 1
    rig.frame()            # pulled before this frame's pass
    assert dr.dream_frame == 1 and src.submitted[1][0].max() > 0
    out = rig.read().astype(int)
    scene = rig.scene().astype(int)
    assert np.abs(out - scene).mean() > 0.5, "the dream layer must show"
    # the third submit answered the second; a result already shown is not
    # uploaded again
    assert dr.pull() is True and dr.dream_frame == 2
    assert dr.pull() is False
    rig.release()


@pytest.mark.slow
def test_copy_path_round_trip_under_budget(ctx):
    """The spike's number: glReadPixels of a 256-px echo into a host array
    plus the upload back is ~0.5 ms; the budget here is 1.5 ms p50."""
    w, h = echo_size(256, 1280, 820)
    rig = Rig(ctx, 1280, 820, dream=DreamState(on=True, res=2))
    rig.frame()
    lb, dr = rig.lb, rig.r.dreamer
    dr._ensure(1280, 820)
    buf = np.empty((h, w, 4), dtype=np.uint8)
    for _ in range(5):
        lb.read_into(buf)
        dr.write_from(buf)
    ctx.finish()
    times = []
    for _ in range(40):
        t0 = time.perf_counter()
        lb.read_into(buf)
        dr.write_from(buf)
        ctx.finish()
        times.append(time.perf_counter() - t0)
    p50 = sorted(times)[len(times) // 2] * 1e3
    print(f"\nread_into + write_from at {w}x{h}: p50 {p50:.2f} ms")
    assert p50 < 1.5, f"{p50:.2f} ms"
    rig.release()


# ---------------------------------------------------------------- params & loadable patches

def registry(dream=None):
    from hyperspace.analysis import Analyser
    from hyperspace.analyzer import Analyzer
    from hyperspace.control import Control
    from hyperspace.params import build_registry

    chain = Analyzer(Analyser())
    audio = SimpleNamespace(chain=chain)
    return build_registry(ViewState(), Control(chain), audio, None, dream=dream)


DREAM_IDS = [
    "dream.on", "dream.mix", "dream.darken",
    "dream.contrast", "dream.hue", "dream.sat", "dream.tint", "dream.tint_from",
    "dream.tint_hue", "dream.tint_sat", "dream.res", "dream.steps", "dream.step",
    "dream.k", "dream.layer", "dream.octaves", "dream.mask_decay", "dream.jitter",
]


def test_dream_params_declared():
    d = DreamState()
    reg = registry(d)
    assert [p.id for p in reg.group("dream")] == DREAM_IDS
    for p in reg.group("dream"):
        assert p.persist, p.id
    # the three that rebuild things — the ring, the atlas, the net's trunk —
    # are a scene-setter's, never a performer's (plan 16 WP5 added the layer)
    rebuild = ("dream.res", "dream.layer")
    assert not any(reg[pid].modulatable for pid in rebuild)
    assert all(reg[pid].modulatable for pid in DREAM_IDS if pid not in rebuild)
    assert reg["dream.res"].names == [str(v) for v in RES]
    assert reg["dream.layer"].names[1] == "conv3_3"
    # the params write the state the compositor reads
    reg["dream.on"].set(True)
    reg["dream.res"].set(3)
    assert d.on and d.res == 3
    # a fresh state stands in when no renderer is passed
    assert "dream.k" in registry()


def test_a_route_on_the_dream_layer_is_dormant():
    """Plan 16 WP5: `dream.layer` is not a performer's — a change makes the
    worker load another trunk. A route onto it does nothing, quietly; a
    scene-setter (the panel, a loadable patch, a key or desk row) still sets it."""
    import glfw

    from hyperspace.bands import CEIL
    from hyperspace.routing import Binding, Bindings, Router

    d = DreamState()
    reg = registry(d)
    layer, mix = reg["dream.layer"], reg["dream.mix"]
    assert not layer.modulatable and layer.persist
    chain = SimpleNamespace(lanes=np.full(8, CEIL))            # every lane at the top
    router = Router(reg, Bindings([
        Binding("lane:0", "dream.layer", "position", 1.0),
        Binding("lane:0", "dream.mix", "push", 0.2),           # the same source, a live row
        Binding("key:Y", "dream.layer", "step", 1),            # a scene-setter row
    ]))
    before, mix0 = d.layer, mix.norm
    for _ in range(3):
        router.modulate(chain)
        reg.apply()
    assert mix.modulated and mix.eff_norm == pytest.approx(min(mix0 + 0.2, 1.0))
    assert not layer.modulated and d.layer == before and layer.value == before
    # the scene-setters: the panel's write, a loadable patch's restore, a key row
    layer.set(2)
    assert d.layer == 2
    snap = reg.snapshot("dream")
    assert snap["dream.layer"] == layer.value
    layer.set(0)
    reg.restore(snap)
    assert d.layer == 2
    router.keys(SimpleNamespace(pressed=lambda key: key == glfw.KEY_Y))
    assert d.layer == 3
    # and it has left the ROUTING page's target list
    from hyperspace import ui_routing

    targets = {p.id for p in ui_routing._targets(SimpleNamespace(reg=reg))}
    assert "dream.mix" in targets and not targets & {"dream.layer", "dream.gap", "dream.res"}


def test_dream_snapshot_round_trip():
    d = DreamState()
    reg = registry(d)
    snap = reg.snapshot("dream")
    assert set(snap) == set(DREAM_IDS)
    reg["dream.mix"].set_value(0.9)
    reg["dream.layer"].set(4)
    reg["dream.on"].set(True)
    assert reg.restore(snap) == []
    assert d.mix == pytest.approx(0.7) and d.layer == 1 and d.on is False


def test_the_dream_module_presets_load(tmp_path):
    """The three dream module presets (the corpus's, seeded into a scratch
    library): listed, `default` the group's default, each landing its values."""
    from hyperspace.library import Library

    d = DreamState()
    reg = registry(d)
    seed(tmp_path, "dream")
    lib = Library(tmp_path, period=0.0)
    lib.attach(reg)
    assert "dream" in lib.groups()
    assert lib.list("dream") == ["default", "tracer-only", "wake"]
    assert lib.default_name("dream") == "default"
    assert lib.load("dream", "tracer-only") == []
    # (plan 36 T4: echoes alone — the dream off; plan 90 H2: the echoes'
    # knobs retired with the look-back, landing quietly as nothing)
    assert not d.on and d.mix == 0.0
    assert lib.load("dream", "default") == []
    assert not d.on and d.mix == pytest.approx(0.7)
    # the default loadable patch is the fresh state: loading it leaves nothing dirty
    assert not lib.is_dirty("dream")
    fresh = DreamState()
    from hyperspace.graphmigrate import lookback_retired
    for pid, v in lib.read("dream", "default")["values"].items():
        if lookback_retired(pid):
            continue
        attr = pid.split(".", 1)[1]
        assert getattr(fresh, attr) == pytest.approx(v), pid


# ---------------------------------------------------------------- the page

def test_lookback_page_draws_headless(tmp_path):
    from imgui_bundle import imgui

    from hyperspace import ui_lookback
    from hyperspace.analysis import Analyser
    from hyperspace.analyzer import Analyzer
    from hyperspace.control import Control
    from hyperspace.library import Library
    from hyperspace.params import build_registry
    from hyperspace.ui import PAGE_KEYS, Panel, apply_style, load_fonts

    assert "lookback" in PAGE_KEYS
    ictx = imgui.create_context()
    try:
        io = imgui.get_io()
        io.display_size = imgui.ImVec2(820, 820)
        io.backend_flags |= imgui.BackendFlags_.renderer_has_textures
        apply_style()
        load_fonts()
        chain = Analyzer(Analyser())
        control = Control(chain)
        audio = SimpleNamespace(chain=chain, on=False, mode="", error="", label="", sr=48000.0)
        view = ViewState()
        lib = Library(tmp_path, period=0.0)
        d = DreamState()
        reg = build_registry(view, control, audio, lib.install, dream=d)
        lib.attach(reg)
        # no renderer: the thumbnail row says so instead of drawing textures
        panel = Panel(control, audio, view, bank=lib.install, registry=reg, library=lib)
        reg["ui.page"].set(PAGE_KEYS.index("lookback"))
        for on in (False, True):
            d.on = on
            imgui.new_frame()
            panel.draw(1 / 60, 60.0)
            imgui.end_frame()
        # a renderer with a live ring: the thumbnails draw as images
        fake = SimpleNamespace(lookback=SimpleNamespace(
            state=d, atlas=SimpleNamespace(glo=1), dream=SimpleNamespace(glo=2),
            echo=(200, 128), dream_frame=3, frame=12,
            thumbnails=lambda: [{"slot": 0, "age": 1, "weight": 0.3, "uv0": (0, 1 / 32),
                                 "uv1": (1, 0)}]))
        panel.renderer = fake
        imgui.new_frame()
        panel.draw(1 / 60, 60.0)
        imgui.end_frame()
        # the page function stands alone as well (hot-reload target)
        imgui.new_frame()
        imgui.begin("x")
        ui_lookback.page(panel, 1 / 60)
        imgui.end()
        imgui.end_frame()
    finally:
        imgui.destroy_context(ictx)


# ---------------------------------------------------------------- plan 20 WP4: ECHOES, DREAM, BOTH

# every dream.* param as it was before plan 20 relabelled the page: id, kind,
# lo, hi, default, persist, modulatable, integer, log, wrap, choices. WP4 and
# WP5 change labels, readouts and tips only; a row that moves here is a
# migration nobody planned.
DREAM_FROZEN = [
    ("dream.on", "TOGGLE", 0.0, 1.0, False, True, True, False, False, False, None),
    ("dream.mix", "CONTINUOUS", 0.0, 1.0, 0.7, True, True, False, False, False, None),
    ("dream.darken", "CONTINUOUS", 0.0, 1.0, 0.1, True, True, False, False, False, None),
    ("dream.contrast", "CONTINUOUS", 0.5, 3.0, 1.0, True, True, False, False, False, None),
    ("dream.hue", "CONTINUOUS", -180.0, 180.0, 0.0, True, True, False, False, True, None),
    ("dream.sat", "CONTINUOUS", 0.0, 2.0, 1.0, True, True, False, False, False, None),
    ("dream.tint", "CONTINUOUS", 0.0, 1.0, 0.0, True, True, False, False, False, None),
    ("dream.tint_from", "ENUM", 0.0, 1.0, 0, True, True, False, False, False,
     ("colour", "scene")),
    ("dream.tint_hue", "CONTINUOUS", 0.0, 360.0, 200.0, True, True, False, False, True, None),
    ("dream.tint_sat", "CONTINUOUS", 0.0, 1.0, 1.0, True, True, False, False, False, None),
    ("dream.res", "ENUM", 0.0, 1.0, 2, True, False, False, False, False,
     ("128", "192", "256", "384")),
    ("dream.steps", "CONTINUOUS", 1, 3, 2, True, True, True, False, False, None),
    ("dream.step", "CONTINUOUS", 0.005, 0.06, 0.03, True, True, False, False, False, None),
    ("dream.k", "CONTINUOUS", 0.03, 0.3, 0.05, True, True, False, False, False, None),
    # the layer's first six keep their indices; every other layer of both
    # nets is appended after them (a loadable patch stores the index)
    ("dream.layer", "ENUM", 0.0, 1.0, 1, True, False, False, False, False,
     ("conv2_2", "conv3_3", "conv4_3", "inception3b", "inception4c", "inception4e",
      "conv1_1", "conv1_2", "conv2_1", "conv3_1", "conv3_2", "conv4_1", "conv4_2",
      "conv5_1", "conv5_2", "conv5_3", "conv1", "conv2", "conv3", "inception3a",
      "inception4a", "inception4b", "inception4d", "inception5a", "inception5b")),
    ("dream.octaves", "ENUM", 0.0, 1.0, 0, True, True, False, False, False,
     ("1", "2 alt", "3 alt")),
    ("dream.mask_decay", "CONTINUOUS", 0.9, 0.995, 0.99, True, True, False, False, False, None),
    ("dream.jitter", "CONTINUOUS", 0, 16, 8, True, True, True, False, False, None),
]


def test_no_dream_id_range_default_or_flag_changed():
    """The relabel is strings only: every `dream.*` param's id, kind,
    bounds, default, `persist`, `modulatable`, taper flags and choices are
    what they were, in the order they were declared — so no saved look, no
    route and no desk row means anything else than it did."""
    from hyperspace.params import Kind

    reg = registry()
    now = [(p.id, p.kind.name, p.lo, p.hi, p.base, p.persist, p.modulatable, bool(p.integer),
            bool(p.log), bool(p.wrap), tuple(p.names) if p.kind is Kind.ENUM else None)
           for p in reg.group("dream")]
    assert now == DREAM_FROZEN
    assert [type(row[4]) for row in now] == [type(row[4]) for row in DREAM_FROZEN]
    assert [row[0] for row in now] == DREAM_IDS
    assert not any(p.alias or p.taper is not None for p in reg.group("dream"))
    assert not [p.id for p in reg if p.id.startswith("dream.") and p.group != "dream"]


class LookbackPage:
    """The LOOKBACK page on a headless imgui context, with what it draws
    recorded in order: section titles, cell labels, widgets (by imgui id,
    with their rectangle and whether a chip was lit) and popup ids."""

    def __init__(self, tmp_path, monkeypatch):
        from imgui_bundle import imgui

        from hyperspace import ui, ui_lookback
        from hyperspace.analysis import Analyser
        from hyperspace.analyzer import Analyzer
        from hyperspace.app import CONTROL_SIZE
        from hyperspace.control import Control
        from hyperspace.library import Library
        from hyperspace.params import build_registry

        self.imgui, self.ui_lookback = imgui, ui_lookback
        self.ictx = imgui.create_context()
        io = imgui.get_io()
        io.display_size = imgui.ImVec2(*CONTROL_SIZE)
        io.backend_flags |= imgui.BackendFlags_.renderer_has_textures
        ui.apply_style()
        ui.load_fonts()
        chain = Analyzer(Analyser())
        control = Control(chain)
        audio = SimpleNamespace(chain=chain, on=False, mode="", error="", label="", sr=48000.0)
        view = ViewState()
        lib = Library(tmp_path, period=0.0)
        self.dream = DreamState()
        self.reg = build_registry(view, control, audio, lib.install, dream=self.dream)
        lib.attach(self.reg)
        self.panel = ui.Panel(control, audio, view, bank=lib.install, registry=self.reg,
                              library=lib)
        self.events: list[tuple[str, str]] = []     # ("title" | "label" | "widget" | "popup", text)
        self.rects: dict[str, tuple[float, float, float, float]] = {}
        self.lit: dict[str, bool] = {}
        red = tuple(ui.RED)

        def item(fn):
            real = getattr(imgui, fn)

            def rec(label, *a, **k):
                key = label.split("##", 1)[-1]
                self.lit[key] = tuple(imgui.get_style_color_vec4(imgui.Col_.button)) == red
                out = real(label, *a, **k)
                lo, hi = imgui.get_item_rect_min(), imgui.get_item_rect_max()
                self.rects[key] = (lo.x, lo.y, hi.x, hi.y)
                self.events.append(("widget", key))
                return out
            monkeypatch.setattr(imgui, fn, rec)
        for fn in ("button", "checkbox", "slider_float", "slider_int", "combo",
                   "invisible_button", "color_button", "begin_combo", "selectable"):
            item(fn)
        real_popup = imgui.begin_popup_context_item

        def popup(str_id, *a, **k):
            self.events.append(("popup", str_id))
            return real_popup(str_id, *a, **k)
        monkeypatch.setattr(imgui, "begin_popup_context_item", popup)
        real_micro = ui._micro

        def micro(text, color=None):
            if color is ui.TEXT:                    # a section's title, not its note
                self.events.append(("title", text))
            return real_micro(text, color)
        monkeypatch.setattr(ui, "_micro", micro)
        real_label = ui.Panel._label_cell

        def label_cell(text, *a, **k):
            self.events.append(("label", text))
            return real_label(text, *a, **k)
        monkeypatch.setattr(ui.Panel, "_label_cell", staticmethod(label_cell))

    def frame(self) -> None:
        imgui = self.imgui
        self.events.clear()
        self.rects.clear()
        self.lit.clear()
        imgui.new_frame()
        imgui.set_next_window_pos(imgui.ImVec2(0, 0))
        imgui.set_next_window_size(imgui.ImVec2(420, 860))
        imgui.begin("page", None, imgui.WindowFlags_.no_title_bar | imgui.WindowFlags_.no_move)
        self.ui_lookback.page(self.panel, 1 / 60)
        imgui.end()
        imgui.end_frame()

    def click(self, item: str, button: int = 0) -> None:
        """A click on the widget whose id is `item`: the mouse moves there,
        presses, releases, and leaves."""
        io = self.imgui.get_io()
        self.frame()
        x0, y0, x1, y1 = self.rects[item]
        io.add_mouse_pos_event((x0 + x1) / 2, (y0 + y1) / 2)
        self.frame()
        io.add_mouse_button_event(button, True)
        self.frame()
        io.add_mouse_button_event(button, False)
        self.frame()
        io.add_mouse_pos_event(-1.0, -1.0)
        self.frame()

    def widgets(self) -> list[str]:
        return [text for kind, text in self.events if kind == "widget"]

    def by_section(self) -> dict[str, list[str]]:
        """Section title → the dream.* params drawn under it, in order (a
        chip's id is ``chip.<param>.<k>``; a widget's is the param's)."""
        out: dict[str, list[str]] = {}
        title = ""
        for kind, text in self.events:
            if kind == "title":
                title = text
                out[title] = []
            elif kind == "widget" and "dream." in text:
                pid = text[text.index("dream."):]
                pid = pid.rsplit(".", 1)[0] if text.startswith("chip.") else pid
                if pid not in out[title]:
                    out[title].append(pid)
        return out

    def close(self) -> None:
        self.imgui.destroy_context(self.ictx)


@pytest.fixture()
def lbpage(tmp_path, monkeypatch):
    page = LookbackPage(tmp_path, monkeypatch)
    yield page
    page.close()


def test_the_page_draws_the_dream_and_every_dream_param_once(lbpage):
    """Plan 49 stage 2 drew the look-back and the dream as two nodes; plan 90
    (H2) retires the look-back's half: under the page's title the DREAM node
    alone, `dream.on` on its head, darken, contrast and detail its own — and
    every persisted `dream.*` param drawn exactly once."""
    from hyperspace import ui_lookback

    lbpage.frame()
    got = lbpage.by_section()
    assert list(got) == ["dream"]
    assert got["dream"][0] == "dream.on"                 # the dream's own switch, on its head
    assert set(got["dream"]) == set(ui_lookback.SECTIONS["dream"])
    drawn = [pid for ids in got.values() for pid in ids]
    assert sorted(drawn) == sorted(DREAM_IDS)
    # one widget per param (the layer: its menu), on or off
    for on in (False, True):
        lbpage.dream.on = on
        lbpage.frame()
        ids = [w for w in lbpage.widgets() if "dream." in w]
        assert sorted(ids) == sorted(DREAM_IDS)
    # every cell has a label, and every label is in the page's table
    labels = [text for kind, text in lbpage.events if kind == "label"]
    cells = [pid for pid in ui_lookback.SECTIONS["dream"]
             if pid not in ("dream.layer", "dream.on")]
    assert [lb for lb in labels if lb != "the tint"] == [ui_lookback.SHORT[pid] for pid in cells]


def test_the_layer_is_one_menu_of_every_layer(lbpage, monkeypatch):
    """`dream.layer` is one combo the row wide and one control tall (no
    taller than the chip row it replaced): closed, it says the layer's
    name and short description; open, every layer of both nets once, under
    a heading per net (not a choice), shallow → deep, each with its long
    description on hover. A pick sets the base — a scene-setter's write and
    one undo step — and the right-click menu is the param's."""
    from hyperspace import ui, ui_lookback, undo
    from hyperspace.lookback import LAYER_INFO, LAYERS
    from hyperspace.routing import Bindings, Router

    reg, d = lbpage.reg, lbpage.dream
    layer = reg["dream.layer"]
    said: list[str] = []
    real_say = ui.tooltip
    monkeypatch.setattr(ui, "tooltip", lambda text: (said.append(text), real_say(text)))
    lbpage.frame()
    assert lbpage.widgets().count("dream.layer") == 1
    assert not [w for w in lbpage.widgets() if w.startswith(("chip.", "layer."))]
    x0, y0, x1, y1 = lbpage.rects["dream.layer"]
    o = lbpage.rects["dream.octaves"]                     # a plain combo cell, one control tall
    assert y1 - y0 == pytest.approx(o[3] - o[1])
    mix = lbpage.rects["dream.tint_sat"]                  # the row is as wide as the two cells
    assert x1 - x0 > 2 * (mix[2] - mix[0])
    # the closed menu's text: the name and its short description
    assert ui_lookback.layer_preview("conv3_3", 1000) == "conv3_3 · small loops, the classic"
    assert ui_lookback.layer_preview("conv3_3", 60).endswith("…")
    # open: every layer once, grouped by net, in the table's order
    lbpage.click("dream.layer")
    lbpage.frame()
    items = [w[len("layer."):] for w in lbpage.widgets() if w.startswith("layer.")]
    assert items == list(LAYER_INFO) and sorted(items) == sorted(LAYERS)
    assert [(net, len(names)) for net, names in ui_lookback.layer_menu()] == [
        ("VGG16", 13), ("GoogLeNet", 12)]
    assert not {"VGG16", "GoogLeNet"} & set(lbpage.widgets())   # headings are not choices
    # a hover says the long description
    io = lbpage.imgui.get_io()
    hx0, hy0, _, hy1 = lbpage.rects["layer.conv1_1"]
    io.add_mouse_pos_event(hx0 + 20, (hy0 + hy1) / 2)
    lbpage.frame()
    lbpage.frame()
    assert any(LAYER_INFO["conv1_1"][2] in s for s in said)
    # a pick: the base, the state, one undo step
    u = undo.Undo(reg, Router(reg, Bindings([])).table)
    u.tick(0.0)
    lbpage.click("layer.conv5_3")
    assert layer.base == LAYERS.index("conv5_3") and d.layer == layer.base
    assert not layer.modulated
    lbpage.frame()
    assert not [w for w in lbpage.widgets() if w.startswith("layer.")]    # it closed
    u.tick(1.0)
    u.tick(2.0)
    assert u.undo() and layer.base == 1 and d.layer == 1
    assert not u.undo()
    # the right-click menu is the param's own, one popup
    lbpage.frame()
    popups = [text for kind, text in lbpage.events if kind == "popup"]
    assert [p for p in popups if "dream.layer" in p] == ["##ctx.dream.layer"]
    lbpage.click("dream.layer", button=1)
    assert d.layer == 1
    assert lbpage.imgui.is_popup_open("", lbpage.imgui.PopupFlags_.any_popup_id)


def test_an_armed_learn_outlines_the_layer_menu(lbpage, monkeypatch):
    """Armed to learn, the layer menu gets the outline every control gets."""
    from hyperspace import ui

    framed: list[str] = []
    real = ui.Panel._learn_frame
    monkeypatch.setattr(ui.Panel, "_learn_frame",
                        lambda self, p: (framed.append(p.id), real(self, p))[1])
    lbpage.panel.learn = SimpleNamespace(learning="dream.layer", arm=lambda pid: None)
    lbpage.frame()
    assert framed.count("dream.layer") == 1 and "dream.mix" in framed


def test_every_dream_label_says_whose_knob_it_is():
    """Fork F9: the registry's labels change with the page's. A dream knob
    says Dream, the two that grade it and the switch say neither (plan 90
    H2: the echo knobs retired with the look-back); every tip opens with a
    sentence."""
    from hyperspace import ui_lookback

    reg = registry()
    for pid in ui_lookback.SECTIONS["dream"]:
        if pid in ("dream.darken", "dream.contrast"):
            continue
        assert reg[pid].label.startswith("Dream "), pid
    assert [reg[pid].label for pid in ("dream.darken", "dream.contrast")] == [
        "Darken", "Contrast"]
    assert reg["dream.on"].label == "Dream on"           # (plan 36 T4: the dream's own)
    labels = [p.label for p in reg.group("dream")]
    assert len(set(labels)) == len(labels)          # ROUTING's list tells every one apart
    for p in reg.group("dream"):
        assert p.tip and (p.tip[0].isupper() or p.tip[0].isdigit()), p.id
    # a readout fits its half-width cell: nothing longer than the slider is wide
    for p in reg.group("dream"):
        if p.fmt is not None and p.kind.name == "CONTINUOUS":
            for v in (p.lo, p.hi, p.base):
                assert len(p.fmt(v)) <= 10, (p.id, p.fmt(v))


def test_the_routing_page_lists_the_new_labels():
    """ROUTING's target list is the registry's labels: it says "Dream
    brightness" where it said "Dream mix", and a search for the page's word
    finds the param."""
    from hyperspace import ui_routing

    reg = registry()
    targets = {p.id: p.label for p in ui_routing._targets(SimpleNamespace(reg=reg))
               if p.id.startswith("dream.")}
    assert targets["dream.mix"] == "Dream brightness"
    assert targets["dream.step"] == "Dream strength"
    assert targets["dream.mask_decay"] == "Dream linger"
    old = {"Echo mix", "Dream mix", "Fade", "Echoes", "Spacing", "Occlude", "Hue shift",
           "Saturation", "Tint", "Step size", "Steps", "Mask decay", "Jitter", "Octaves",
           "Layer", "Resolution"}
    assert not old & set(targets.values())
    # the three that rebuild things are still not a performer's
    assert not set(targets) & {"dream.res", "dream.layer"}


# ---------------------------------------------------------------- plan 20 WP5: dream speed

def test_dream_speed_is_dream_k(lbpage):
    """Fork F8: the dream's "speed" is `dream.k`, relabelled — one cell
    labelled SPEED drawing that param in the DREAM section's first row,
    beside BRIGHTNESS; no `dream.speed` and no other new id; the registry
    (ROUTING, Learn, the desk) says "Dream speed"; and nothing else about
    the param moved, so every saved look means what it did."""
    from hyperspace import ui_lookback, ui_routing

    reg = lbpage.reg
    k = reg["dream.k"]
    assert "dream.speed" not in reg
    assert [p.id for p in reg.group("dream")] == DREAM_IDS
    assert k.label == "Dream speed" and ui_lookback.SHORT["dream.k"] == "speed"
    assert (k.lo, k.hi, k.base, k.persist, k.modulatable) == (0.03, 0.3, 0.05, True, True)
    assert not k.log and not k.integer and k.taper is None
    assert k.tip.startswith("How fast the dream follows the picture")
    assert "dream frames" in k.tip and "step clamped" in k.tip
    lbpage.frame()
    events = lbpage.events
    labels = [text for kind, text in events if kind == "label"]
    assert labels.count("speed") == 1
    at = events.index(("label", "speed"))
    assert events[at + 1] == ("widget", "dream.k")
    assert lbpage.widgets().count("dream.k") == 1
    # the DREAM section's first row: brightness, then speed, on one line
    cells = [w for w in lbpage.by_section()["dream"] if w not in ("dream.layer", "dream.on")]
    assert cells[:2] == ["dream.mix", "dream.k"]
    mix, speed = lbpage.rects["dream.mix"], lbpage.rects["dream.k"]
    assert round(mix[1]) == round(speed[1]) and mix[2] < speed[0]
    # right is faster: the slider's value is k itself, and it writes the state
    k.set_value(0.2)
    assert lbpage.dream.k == pytest.approx(0.2)
    # ROUTING lists it under the new name; a loadable patch still carries the old id
    assert {p.id: p.label for p in ui_routing._targets(SimpleNamespace(reg=reg))}[
        "dream.k"] == "Dream speed"
    assert reg.snapshot("dream")["dream.k"] == pytest.approx(0.2)


def test_the_speed_readout_is_the_half_life_in_frames():
    """The readout is the frames in which a frame's share of the dream
    halves, log ½ / log(1 − k), rounded: 14 at the default, 2 at the fast
    end, 23 at the slow end — and fewer frames the further right."""
    from hyperspace.params import dream_half_life

    reg = registry()
    k = reg["dream.k"]
    assert k.text() == "≈14 frames"                         # the default, 0.05
    for value, reads in ((0.05, "≈14 frames"), (0.3, "1.9 frames"), (0.03, "≈23 frames"),
                         (0.04, "≈17 frames"), (0.1, "6.6 frames")):
        k.set_value(value)
        assert k.text() == reads, value
        assert k.fmt(value) == reads
    assert (k.fmt(k.lo), k.fmt(k.hi)) == ("≈23 frames", "1.9 frames")
    # it is the half-life: after that many frames a frame's share is about a half
    for value in (0.03, 0.05, 0.1, 0.3):
        n = dream_half_life(value)
        assert (1 - value) ** (n - 0.5) > 0.5 > (1 - value) ** (n + 0.5)
    # monotone across the knob, and safe off its ends (a performer's overshoot is clamped
    # by the registry, but the format must not raise on any float)
    frames = [dream_half_life(0.03 + 0.27 * i / 50) for i in range(51)]
    assert frames == sorted(frames, reverse=True)
    assert dream_half_life(0.0) >= 1 and dream_half_life(1.0) == 1 and dream_half_life(2.0) == 1
    for bad in (float("nan"), float("inf"), -float("inf")):
        assert dream_half_life(bad) == 1 and k.fmt(bad) == "≈1 frames"
    # under ten frames the readout carries a decimal, so the fast end of the
    # knob does not read "≈2 frames" over nearly half its travel
    fast = [k.fmt(0.2 + 0.1 * i / 10) for i in range(11)]
    assert len(set(fast)) >= 8, fast
    # the speed's readout fits its half-width cell like the others
    assert max(len(k.fmt(v)) for v in (k.lo, k.hi, 0.05)) <= 10


def test_the_look_back_page_has_no_conflicting_ids(lbpage):
    """Every widget on the page has its own imgui id and its own popup:
    two cells are both called BRIGHTNESS."""
    for on in (False, True):
        lbpage.dream.on = on
        lbpage.frame()
        ids = lbpage.widgets()
        assert not {i for i in ids if ids.count(i) > 1}
        popups = [text for kind, text in lbpage.events if kind == "popup"]
        assert not {i for i in popups if popups.count(i) > 1}
        # every dream.* widget offers its param's menu
        assert {p[len("##ctx."):] for p in popups} >= set(DREAM_IDS)


def test_the_worker_status_is_never_taller_than_its_room(lbpage):
    """The worker's line is cut to STATUS_LINES with an ellipsis, so what
    it has to say cannot push the page into scrolling; a short one is
    drawn whole."""
    from hyperspace import ui_lookback

    imgui = lbpage.imgui
    imgui.new_frame()
    short = "mps · alias · conv3_3 fp32 · 11.3 ms · 1 behind"
    long = " · ".join([short, "3456 dropped", "12 nan reset(s)", "step clamped"] + ["x" * 30] * 8)
    h = imgui.get_text_line_height()
    assert ui_lookback.fit_lines(short, 380.0, 3) == short
    cut = ui_lookback.fit_lines(long, 380.0, 3)
    assert cut.endswith("…") and long.startswith(cut[:-1].rstrip()) and len(cut) > 100
    assert imgui.calc_text_size(cut, wrap_width=380.0).y <= 3 * h + 0.5
    assert imgui.calc_text_size(long, wrap_width=380.0).y > 3 * h + 0.5
    imgui.end_frame()


def test_the_relabel_reaches_no_loadable_file(tmp_path):
    """Labels are not in loadable patch files: the dream module presets name ids
    only (and, from before plan 90 H2, the look-back's retired ones)."""
    from hyperspace.graphmigrate import lookback_retired
    from hyperspace.library import Library

    reg = registry()
    seed(tmp_path / "home", "dream")
    lib = Library(tmp_path / "home", period=0.0)
    lib.attach(reg)
    for name in lib.list("dream"):
        ids = {k for k in lib.read("dream", name)["values"] if not lookback_retired(k)}
        assert ids <= set(DREAM_IDS), name


# ---------------------------------------------------------------- plan 14 WP1: the freeze


# ---------------------------------------------------------------- the dream layer menu

# what `dream.layer`'s stored index meant before every layer was offered
LAYERS_BEFORE = ["conv2_2", "conv3_3", "conv4_3", "inception3b", "inception4c", "inception4e"]


def test_every_layer_has_its_words():
    """Each name in LAYERS is in LAYER_INFO once (and nothing else is),
    with a net, a short line that fits the closed menu beside the name and
    a longer one; the menu is grouped by net, VGG16 first."""
    from hyperspace.lookback import LAYER_INFO, LAYERS

    assert len(LAYERS) == len(set(LAYERS)) == 25
    assert set(LAYER_INFO) == set(LAYERS)
    nets = [net for net, _, _ in LAYER_INFO.values()]
    assert nets == ["VGG16"] * 13 + ["GoogLeNet"] * 12
    for name, (_, short, long) in LAYER_INFO.items():
        assert short and len(short) <= 26 and "\n" not in short, name
        assert len(long) > len(short) and long.endswith("."), name
        assert ("slower" in short) == ("Slower" in long), name


def test_saved_layers_keep_their_meaning():
    """`dream.layer` is stored as an index, so the six layers there were
    keep their indices and the rest are appended: every corpus and fixture
    file that names a layer gets the same layer by name as before."""
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    reg = registry()
    layer = reg["dream.layer"]
    assert layer.names[:6] == LAYERS_BEFORE

    def found(doc):
        if isinstance(doc, dict):
            for k, v in doc.items():
                if k == "dream.layer":
                    yield v
                else:
                    yield from found(v)
        elif isinstance(doc, list):
            for v in doc:
                yield from found(v)

    seen = 0
    for f in sorted([*(root / "tests" / "corpus").rglob("*.json"),
                     *(root / "tests" / "fixtures").rglob("*.json")]):
        for v in found(json.loads(f.read_text())):
            assert isinstance(v, int) and 0 <= v < len(LAYERS_BEFORE), f
            reg.restore({"dream.layer": v})
            assert layer.names[layer.base] == LAYERS_BEFORE[v], f
            seen += 1
    # the corpus's looks; the owner's shared/ snapshot went in plan 25, and
    # the names[:6] check above covers every index a saved file can hold
    assert seen >= 4


