"""WP6a — the look-back core: history ring, age-weighted composite, the
dream slot's copy path, the dream.* params and their presets, the page.

Everything runs offscreen on a standalone GL context (skipped where there
is none). The composite is checked against a numpy transcription of the
shader's math at the echo's own size, so sampling is one-to-one and the
only tolerance is 8-bit rounding.
"""

from __future__ import annotations

import time
from types import SimpleNamespace

import numpy as np
import pytest

moderngl = pytest.importorskip("moderngl")

from hyperspace.lookback import (
    MAX_ECHOES,
    RES,
    DreamState,
    LookbackSource,
    NullSource,
    echo_size,
)
from hyperspace.render import Renderer, ViewState

VIEW = {"ang": [0.3, 0.7, 1.1, 0.5, 0.9, 1.3], "yaw": 0.4, "pitch": 0.25}


@pytest.fixture(scope="module")
def ctx():
    try:
        c = moderngl.create_context(standalone=True)
    except Exception as e:  # noqa: BLE001 — any GL failure means skip
        pytest.skip(f"no standalone GL context available: {e}")
    yield c
    c.release()


class Rig:
    """A renderer on an RGBA texture target of size (w, h), read back as arrays."""

    def __init__(self, ctx, w, h, bg_alpha=1.0, dream=None):
        self.ctx, self.w, self.h = ctx, w, h
        self.tex = ctx.texture((w, h), 4)
        self.fbo = ctx.framebuffer(color_attachments=[self.tex])
        self.r = Renderer(ctx, dream)
        self.r.bg_alpha = bg_alpha
        self.lb = self.r.lookback
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


def test_ring_depth_and_age(ctx):
    rig = Rig(ctx, 200, 128, dream=DreamState(on=True, echoes=4, every=1, res=0))
    lb = rig.lb
    assert lb.layers() == []
    for _ in range(3):
        rig.frame()
    # three captures, aged against the frame about to be drawn: 3, 2, 1
    assert lb.frame == 3
    assert [age for _, age in lb.layers()] == [3, 2, 1]
    for _ in range(5):
        rig.frame()
    # the ring holds the newest `echoes`, oldest first
    assert [age for _, age in lb.layers()] == [4, 3, 2, 1]
    slots = [slot for slot, _ in lb.layers()]
    assert len(set(slots)) == 4 and all(0 <= s < MAX_ECHOES for s in slots)
    # weights are echo_mix · decay^age
    lb.state.echo_mix, lb.state.decay = 0.5, 0.8
    assert [w for _, w in lb.weights()] == pytest.approx([0.5 * 0.8 ** a for a in (4, 3, 2, 1)])
    # a shallower ring drops the oldest; zero composites nothing
    lb.state.echoes = 2
    assert [age for _, age in lb.layers()] == [2, 1]
    lb.state.echoes = 0
    assert lb.layers() == []
    rig.release()


def test_capture_cadence(ctx):
    rig = Rig(ctx, 200, 128, dream=DreamState(on=True, echoes=8, every=3, res=0))
    for _ in range(9):
        rig.frame()
    # captures land on frames 3, 6, 9 → ages 7, 4, 1 against frame 10
    assert [age for _, age in rig.lb.layers()] == [7, 4, 1]
    rig.release()


def test_off_forgets_the_history(ctx):
    rig = Rig(ctx, 200, 128, dream=DreamState(on=True, echoes=4, every=1, res=0))
    for _ in range(4):
        rig.frame()
    assert len(rig.lb.layers()) == 4
    rig.lb.state.on = False
    rig.frame()
    assert rig.lb.layers() == []
    rig.lb.state.on = True
    rig.frame()
    assert [age for _, age in rig.lb.layers()] == [1]
    rig.release()


def test_res_rebuilds_the_atlas(ctx):
    rig = Rig(ctx, 400, 256, dream=DreamState(on=True, echoes=4, every=1, res=0))
    rig.frame()
    assert rig.lb.echo == (200, 128)
    assert rig.lb.atlas.size == (200, 128 * MAX_ECHOES)
    rig.lb.state.res = 2
    rig.frame()
    assert rig.lb.echo == (400, 256)
    assert rig.lb.dream.size == (400, 256)
    assert ctx.error == "GL_NO_ERROR"
    rig.release()


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


def test_composite_matches_numpy_reference(ctx):
    # target at the echo size, so atlas sampling is one texel per pixel
    w, h = echo_size(128, 400, 256)
    rig = Rig(ctx, w, h, dream=DreamState(on=True, echoes=3, every=1, res=0,
                                          echo_mix=0.7, decay=0.8, darken=0.25, contrast=1.6,
                                          mix=0.5))
    rig.frame()                        # builds the ring; one real capture in slot 0
    lb = rig.lb
    assert lb.echo == (w, h)
    imgs = [synthetic(h, w, k) for k in range(3)]
    lb.frame = 10                      # slot 0's capture (frame 1) falls off the ring
    now = lb.frame + 1
    for k, img in enumerate(imgs):     # slots 1..3 hold frames aged 3, 2, 1
        lb.write_slot(k + 1, img, frame_index=now - 3 + k)
    assert [age for _, age in lb.layers()] == [3, 2, 1]
    dream = synthetic(h, w, 9)
    lb.write_from(dream, frame_index=now - 1)
    rig.fbo.use()
    ctx.viewport = (0, 0, w, h)
    lb.composite(rig.r.scene.tex, rig.fbo)
    out = rig.read().astype(np.float64) / 255.0
    scene = rig.scene().astype(np.float64) / 255.0
    layers = [(img.astype(np.float64) / 255.0, 0.7 * 0.8 ** age)
              for img, age in zip(imgs, (3, 2, 1))]
    layers.append((dream.astype(np.float64) / 255.0, 0.5))
    ref = reference(scene, layers, 0.25, 1.6)
    err = np.abs(out - ref)
    assert err.max() <= 2.5 / 255, f"max error {err.max() * 255:.2f}/255"
    assert err.mean() <= 0.4 / 255
    # the wake is really there: the composite is not the scene
    assert np.abs(out - scene).mean() > 0.02
    # the black quarter of every layer adds nothing over the scene
    assert np.array_equal((out[:, : w // 4] * 255).round(), (scene[:, : w // 4] * 255).round())
    rig.release()


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
    """The chroma stage on the dream buffer alone (no echoes): the shader
    against the numpy transcription, tint colour included — the chosen
    one, or the hue of the scene's mean, read off the newest echo at
    capture."""
    import colorsys

    w, h = echo_size(128, 400, 256)
    # occlude 0: the scene here is lit everywhere and would cover it all
    state = DreamState(on=True, echoes=0, every=1, res=0, darken=0.2, contrast=1.3, mix=0.6,
                       occlude=0.0, **chroma_kw)
    rig = Rig(ctx, w, h, dream=state)
    rig.frame()
    lb = rig.lb
    # a scene with a decided colour cast, captured as the frame loop would
    # (the echo is the scene itself here: target at the echo size)
    scene8 = synthetic(h, w, 21)
    scene8[..., :3] = (scene8[..., :3] * np.array([0.25, 0.55, 1.0])).round().astype(np.uint8)
    rig.r.scene.tex.write(scene8)
    rig.fbo.use()
    ctx.viewport = (0, 0, w, h)
    lb.capture(rig.r.scene.tex, rig.fbo)
    dream8 = synthetic(h, w, 9)
    lb.write_from(dream8, frame_index=lb.frame)
    lb.composite(rig.r.scene.tex, rig.fbo)
    out = rig.read().astype(np.float64) / 255.0
    scene = scene8.astype(np.float64) / 255.0
    dream = dream8.astype(np.float64)[..., :3] / 255.0
    if tint_rgb == "scene":
        from hyperspace.lookback import mean_colour, scene_tint

        # the composite's colour is off the strided mean of the echo, which
        # sits on the exact mean's hue to within a degree or so
        exact = scene_hue_tint(scene, state.tint_sat)
        assert max(exact) - min(exact) > 0.5, "the cast must give a real hue"
        assert lb.scene_mean == pytest.approx(mean_colour(scene8), abs=1e-6)
        assert lb.scene_mean == pytest.approx(scene[..., :3].reshape(-1, 3).mean(axis=0),
                                              abs=0.01)
        tint_rgb = lb.tint_rgb()
        assert tint_rgb == pytest.approx(scene_tint(mean_colour(scene8), state.tint_sat))
        assert tint_rgb == pytest.approx(exact, abs=0.03)
    elif tint_rgb is None:
        tint_rgb = colorsys.hsv_to_rgb(state.tint_hue / 360.0, state.tint_sat, 1.0)
        assert lb.scene_mean is None, "colour mode never reads the echo back"
    coloured = chroma(dream, state.hue, state.sat, state.tint, tint_rgb)
    rgba = np.concatenate([coloured, np.ones(coloured.shape[:2] + (1,))], axis=2)
    ref = reference(scene, [(rgba, 0.6)], 0.2, 1.3, occlude=0.0)
    err = np.abs(out - ref)
    assert err.max() <= 2.5 / 255, f"max error {err.max() * 255:.2f}/255"
    assert err.mean() <= 0.4 / 255
    assert np.abs(out - scene).mean() > 0.02, "the dream is really there"
    # the black quarter of the dream adds nothing whatever its chroma
    assert np.array_equal((out[:, : w // 4] * 255).round(), (scene[:, : w // 4] * 255).round())
    rig.release()


@pytest.mark.parametrize("occlude", [0.0, 0.5, 1.0])
def test_render_occludes_the_wake(ctx, occlude):
    """The render over the wake: a lit shape covers the dream beneath it by
    its brightness × occlude; between the shapes the dream shows whole."""
    w, h = echo_size(128, 400, 256)
    d = DreamState(on=True, echoes=0, every=1, res=0, darken=0.0, contrast=1.0, mix=1.0,
                   occlude=occlude)
    rig = Rig(ctx, w, h, dream=d)
    rig.frame()
    # a scene: a bright bar and a faint bar on black; a flat grey dream everywhere
    scene8 = np.zeros((h, w, 4), dtype=np.uint8)
    scene8[..., 3] = 255
    scene8[:, 40:60, :3] = 200           # bright: covers fully at occlude 1
    scene8[:, 100:120, :3] = 20          # faint: 20/255 × 4 ≈ 31 % coverage
    rig.r.scene.tex.write(scene8)
    dream8 = np.full((h, w, 4), 100, dtype=np.uint8)
    rig.lb.write_from(dream8, frame_index=rig.lb.frame)
    rig.fbo.use()
    ctx.viewport = (0, 0, w, h)
    rig.lb.composite(rig.r.scene.tex, rig.fbo)
    out = rig.read().astype(np.float64) / 255.0
    ref = reference(scene8 / 255.0, [(dream8 / 255.0, 1.0)], 0.0, 1.0, occlude=occlude)
    assert np.abs(out - ref).max() <= 1.5 / 255
    # between the shapes: the dream, whatever occlude is
    assert np.abs(out[:, 150:, 0] - 100 / 255).max() <= 1 / 255
    # on the bright bar: the render alone at occlude 1, render + dream at 0
    bar = out[:, 40:60, 0]
    want = 200 / 255 + (1.0 - occlude) * 100 / 255
    assert np.abs(bar - min(want, 1.0)).max() <= 1.5 / 255
    rig.release()


@pytest.mark.parametrize("bg_alpha", [1.0, 0.0])
def test_faces_occlude_the_dream_whatever_their_fill(ctx, bg_alpha):
    """The bug this guards: faces are filled at a few percent alpha, so
    their brightness alone barely covered the wake and the dream showed
    through them at occlude 1. The faces' coverage mask covers it fully,
    on an opaque ground and on overlay's see-through one."""
    w, h = 320, 240
    d = DreamState(on=True, echoes=0, every=1, res=0, mix=1.0, darken=0.0, occlude=1.0)
    rig = Rig(ctx, w, h, bg_alpha=bg_alpha, dream=d)
    rig.s.faces, rig.s.lines, rig.s.points = True, False, False
    rig.frame()
    lb = rig.lb
    ew, eh = lb.echo
    lb.write_from(np.full((eh, ew, 4), 180, dtype=np.uint8), frame_index=lb.frame)
    rig.frame()
    out, scene = rig.read().astype(int), rig.scene().astype(int)
    faces = np.frombuffer(rig.r.cover.tex.read(), dtype=np.uint8).reshape(h, w) > 0
    assert faces.mean() > 0.05, "the shape must cover some of the frame"
    # brightness alone would have let the dream through most of the faces
    assert (scene[..., :3].max(axis=2)[faces] * 4 < 255).mean() > 0.5
    # …the mask does not: inside a face the output is the render, exactly
    assert np.abs(out[faces] - scene[faces]).max() <= 1
    # between the shapes the dream shows
    assert (out[~faces][:, :3] > scene[~faces][:, :3] + 60).all(axis=1).mean() > 0.9
    # and at occlude 0 it shows through the faces again
    d.occlude = 0.0
    rig.s.ang[3] -= 0.03                 # the same pose as the frame just read
    rig.frame()
    out0 = rig.read().astype(int)
    assert (out0[faces][:, :3] > scene[faces][:, :3] + 60).all(axis=1).mean() > 0.9
    rig.release()


def test_dream_chroma_is_neutral_by_default(ctx):
    """Fresh state: hue 0, sat 1, tint 0 leaves the dream as the net painted it."""
    w, h = echo_size(128, 400, 256)
    d = DreamState(on=True, echoes=0, every=1, res=0, darken=0.0, contrast=1.0, mix=1.0)
    assert (d.hue, d.sat, d.tint) == (0.0, 1.0, 0.0)
    rig = Rig(ctx, w, h, dream=d)
    rig.frame()
    dream8 = synthetic(h, w, 9)
    rig.lb.write_from(dream8, frame_index=rig.lb.frame)
    rig.r.scene.tex.write(np.zeros((h, w, 4), dtype=np.uint8))     # a black scene
    rig.fbo.use()
    ctx.viewport = (0, 0, w, h)
    rig.lb.composite(rig.r.scene.tex, rig.fbo)
    out = rig.read().astype(int)
    # weight 1 over black: the composite is the dream itself (8-bit rounding)
    assert np.abs(out[..., :3] - dream8.astype(int)[..., :3]).max() <= 1
    rig.release()


def test_dream_chroma_tints_the_dream_only(ctx):
    """An echo keeps the scene's colours whatever the dream's tint."""
    w, h = echo_size(128, 400, 256)
    d = DreamState(on=True, echoes=1, every=1, res=0, darken=0.0, contrast=1.0, mix=0.0,
                   echo_mix=1.0, decay=1.0, tint=1.0, tint_hue=120.0, tint_sat=1.0)
    rig = Rig(ctx, w, h, dream=d)
    rig.frame()
    red = np.zeros((h, w, 4), dtype=np.uint8)
    red[..., 0] = red[..., 3] = 255
    rig.lb.write_slot(0, red, frame_index=rig.lb.frame)
    rig.r.scene.tex.write(np.zeros((h, w, 4), dtype=np.uint8))
    rig.fbo.use()
    ctx.viewport = (0, 0, w, h)
    rig.lb.composite(rig.r.scene.tex, rig.fbo)
    out = rig.read()
    assert out[..., 0].min() == 255 and out[..., 1:3].max() == 0, "the echo stays red"
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
    """Scene mode costs one echo read-back a frame, on the cadence or off
    it; colour mode never reads. With a source attached the worker's own
    read serves both. Switching off clears the mean."""
    w, h = echo_size(128, 400, 256)
    d = DreamState(on=True, echoes=2, every=3, res=0, tint_from=1)
    rig = Rig(ctx, w, h, dream=d)
    lb = rig.lb
    for _ in range(4):
        rig.frame()
    assert lb.scene_mean is not None
    assert len(lb.layers()) == 1, "an off-cadence frame is read for the mean, not kept"
    mean = lb.scene_mean
    d.tint_from = 0
    lb.scene_mean = None
    for _ in range(3):
        rig.frame()
    assert lb.scene_mean is None
    d.tint_from = 1
    src = Echo()
    lb.source = src
    n = src.buffers
    rig.frame()
    assert src.buffers == n + 1 and lb.scene_mean is not None
    assert lb.scene_mean == pytest.approx(mean, abs=0.05)   # the same scene, near enough
    d.on = False
    rig.frame()
    assert lb.scene_mean is None
    rig.release()


def test_composite_is_a_copy_when_nothing_is_layered(ctx):
    rig = Rig(ctx, 200, 128, dream=DreamState(on=True, echoes=0, every=1, res=0))
    rig.frame()
    rig.frame()
    assert np.array_equal(rig.read(), rig.scene())
    rig.release()


def test_alpha_preserved_on_a_transparent_ground(ctx):
    """Overlay mode: the ground clears to alpha 0. The wake may only raise
    alpha where an echo has light — premultiplied, colour ≤ coverage — and
    where nothing ever was the desktop stays clear."""
    w, h = echo_size(128, 400, 256)
    rig = Rig(ctx, w, h, bg_alpha=0.0,
              dream=DreamState(on=True, echoes=6, every=1, res=0, echo_mix=0.8, decay=0.9,
                               darken=0.0, contrast=1.0))
    rig.s.faces = True
    for _ in range(7):
        rig.frame()
    out = rig.read().astype(int)
    scene = rig.scene().astype(int)
    assert (scene[..., 3] == 0).any(), "the ground must be see-through"
    assert (out[..., 3] >= scene[..., 3]).all()
    assert (out[..., 3] > scene[..., 3]).any(), "the wake must show somewhere"
    # alpha rises only where the wake has light: a pixel the wake left
    # black keeps the scene's alpha exactly
    lit = (out[..., :3] > scene[..., :3]).any(axis=2)
    assert (out[..., 3][~lit] == scene[..., 3][~lit]).all()
    # the corners never saw content: still fully clear
    assert out[:8, :8].max() == 0 and out[-8:, -8:].max() == 0
    rig.release()


def test_cut_through_toggle_on_an_opaque_ground(ctx):
    """Faces on an opaque ground: cut-through on (the default) lowers the
    window's alpha under the fills; off, every pixel stays opaque."""
    rig = Rig(ctx, 256, 256, bg_alpha=1.0)
    rig.s.faces, rig.s.lines, rig.s.points = True, False, False
    assert rig.s.cut_through
    rig.frame()
    assert rig.read()[..., 3].min() < 255, "the fills must cut the alpha"
    rig.s.cut_through = False
    rig.frame()
    out = rig.read()
    assert (out[..., 3] == 255).all()
    assert out[..., :3].max() > 0, "the fills must still draw"
    rig.release()


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
    assert isinstance(NullSource(), LookbackSource)
    assert isinstance(Echo(), LookbackSource)
    n = NullSource()
    n.submit(np.zeros((2, 2, 4), np.uint8), 7)
    assert n.frame_index == 7 and n.latest() is None


def test_dream_slot_round_trip(ctx):
    w, h = echo_size(128, 400, 256)
    src = Echo()
    rig = Rig(ctx, w, h, dream=DreamState(on=True, echoes=0, every=1, res=0, mix=1.0,
                                          darken=0.0))
    rig.lb.source = src
    rig.frame()
    frame1, idx = src.submitted[-1]
    assert idx == 1 and frame1.shape == (h, w, 4) and src.buffers == 1
    # the submitted pixels are the newest echo: a downsample of the scene
    assert frame1.max() > 0
    # nothing answered yet: the composite is a copy
    assert rig.lb.dream_frame == -1
    rig.frame()            # submit 2; latest() now answers submit 1
    rig.frame()            # pulled before this composite
    assert rig.lb.dream_frame == 1
    out = rig.read().astype(int)
    scene = rig.scene().astype(int)
    assert (out[..., :3] >= scene[..., :3]).all()
    assert np.abs(out - scene).mean() > 0.5, "the dream layer must show"
    # the third capture's submit answered the second; a result already
    # shown is not uploaded again
    assert rig.lb.pull() is True and rig.lb.dream_frame == 2
    assert rig.lb.pull() is False
    rig.release()


def test_read_write_legs(ctx):
    w, h = echo_size(128, 400, 256)
    rig = Rig(ctx, w, h, dream=DreamState(on=True, echoes=1, every=1, res=0))
    rig.frame()
    lb = rig.lb
    buf = np.zeros((h, w, 4), dtype=np.uint8)
    lb.read_into(buf)
    assert buf.max() > 0
    # what came out of the slot is what write_slot put in
    img = synthetic(h, w, 3)
    lb.write_slot(lb.newest(), img)
    lb.read_into(buf)
    assert np.array_equal(buf, img)
    lb.write_from(img, 5)
    assert lb.dream_frame == 5
    back = np.frombuffer(lb.dream.read(), dtype=np.uint8).reshape(h, w, 4)
    assert np.array_equal(back, img)
    rig.release()


@pytest.mark.slow
def test_copy_path_round_trip_under_budget(ctx):
    """The spike's number: glReadPixels of a 256-px echo into a host array
    plus the upload back is ~0.5 ms; the budget here is 1.5 ms p50."""
    w, h = echo_size(256, 1280, 820)
    rig = Rig(ctx, 1280, 820, dream=DreamState(on=True, echoes=1, every=1, res=2))
    rig.frame()
    lb = rig.lb
    buf = np.empty((h, w, 4), dtype=np.uint8)
    for _ in range(5):
        lb.read_into(buf)
        lb.write_from(buf)
    ctx.finish()
    times = []
    for _ in range(40):
        t0 = time.perf_counter()
        lb.read_into(buf)
        lb.write_from(buf)
        ctx.finish()
        times.append(time.perf_counter() - t0)
    p50 = sorted(times)[len(times) // 2] * 1e3
    print(f"\nread_into + write_from at {w}x{h}: p50 {p50:.2f} ms")
    assert p50 < 1.5, f"{p50:.2f} ms"
    rig.release()


# ---------------------------------------------------------------- params & presets

def registry(dream=None):
    from hyperspace.analysis import Analyser
    from hyperspace.bands import Chain
    from hyperspace.control import Control
    from hyperspace.params import build_registry

    chain = Chain(Analyser())
    audio = SimpleNamespace(chain=chain)
    return build_registry(ViewState(), Control(chain), audio, None, dream=dream)


DREAM_IDS = [
    "dream.on", "dream.mix", "dream.echo_mix", "dream.decay", "dream.darken",
    "dream.contrast", "dream.occlude", "dream.hue", "dream.sat", "dream.tint", "dream.tint_from",
    "dream.tint_hue", "dream.tint_sat",
    "dream.echoes", "dream.every", "dream.res", "dream.steps", "dream.step",
    "dream.k", "dream.layer", "dream.octaves", "dream.mask_decay", "dream.jitter",
]


def test_dream_params_declared():
    d = DreamState()
    reg = registry(d)
    assert [p.id for p in reg.group("dream")] == DREAM_IDS
    for p in reg.group("dream"):
        assert p.persist, p.id
    assert not reg["dream.every"].modulatable and not reg["dream.res"].modulatable
    assert all(reg[pid].modulatable for pid in DREAM_IDS
               if pid not in ("dream.every", "dream.res"))
    assert reg["dream.res"].names == [str(v) for v in RES]
    assert reg["dream.layer"].names[1] == "conv3_3"
    # the params write the state the compositor reads
    reg["dream.on"].set(True)
    reg["dream.echoes"].set_value(8)
    reg["dream.res"].set(3)
    assert d.on and d.echoes == 8 and d.res == 3
    # a fresh state stands in when no renderer is passed
    assert "dream.k" in registry()


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


def test_factory_presets_load(tmp_path):
    from hyperspace.library import Library

    d = DreamState()
    reg = registry(d)
    lib = Library(tmp_path, period=0.0)
    lib.attach(reg)
    assert "dream" in lib.groups()
    assert lib.list("dream") == ["default", "tracer-only", "wake"]
    assert lib.default_name("dream") == "default"
    assert lib.load("dream", "tracer-only") == []
    assert d.on and d.echoes == 8 and d.mix == 0.0 and d.echo_mix > 0
    assert lib.load("dream", "default") == []
    assert not d.on and d.echoes == 8 and d.mix == pytest.approx(0.7)
    # the default preset is the fresh state: loading it leaves nothing dirty
    assert not lib.is_dirty("dream")
    fresh = DreamState()
    for pid, v in lib.read("dream", "default")["values"].items():
        attr = pid.split(".", 1)[1]
        assert getattr(fresh, attr) == pytest.approx(v), pid


# ---------------------------------------------------------------- the page

def test_lookback_page_draws_headless(tmp_path):
    from imgui_bundle import imgui

    from hyperspace import ui_lookback
    from hyperspace.analysis import Analyser
    from hyperspace.bands import Chain
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
        chain = Chain(Analyser())
        control = Control(chain)
        audio = SimpleNamespace(chain=chain, on=False, mode="", error="", label="", sr=48000.0)
        view = ViewState()
        lib = Library(tmp_path, period=0.0)
        d = DreamState()
        reg = build_registry(view, control, audio, lib.bank, dream=d)
        lib.attach(reg)
        # no renderer: the thumbnail row says so instead of drawing textures
        panel = Panel(control, audio, view, presets=lib.bank, registry=reg, library=lib)
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
