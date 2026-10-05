"""WP6a — the look-back core: history ring, age-weighted composite, the
dream slot's copy path, the dream.* params and their presets, the page.

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

moderngl = pytest.importorskip("moderngl")

from hyperspace.lookback import (
    FADE_HI,
    MAX_ECHOES,
    REF_HZ,
    RES,
    DreamState,
    Lookback,
    LookbackSource,
    echo_size,
    fade_of_decay,
)
from hyperspace.overlay import Output
from hyperspace.render import Renderer
from hyperspace.view import ViewState

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
    rig = Rig(ctx, 200, 128, dream=DreamState(on=True, echoes=4, gap=0.0, res=0))
    lb = rig.lb
    assert lb.layers() == []
    for _ in range(3):
        rig.frame()
    # three captures, aged against the frame about to be drawn: 3, 2, 1
    assert lb.frame == 3
    assert [round(age * REF_HZ) for _, age in lb.layers()] == [3, 2, 1]
    for _ in range(5):
        rig.frame()
    # the ring holds the newest `echoes`, oldest first
    assert [round(age * REF_HZ) for _, age in lb.layers()] == [4, 3, 2, 1]
    slots = [slot for slot, _ in lb.layers()]
    assert len(set(slots)) == 4 and all(0 <= s < MAX_ECHOES for s in slots)
    # weights are echo_mix · ½^(age / fade): at 60 Hz, echo_mix · decay^frames
    lb.state.echo_mix, lb.state.fade = 0.5, fade_of_decay(0.8)
    assert [w for _, w in lb.weights()] == pytest.approx([0.5 * 0.8 ** a for a in (4, 3, 2, 1)],
                                                          rel=1e-3)
    # a shallower ring drops the oldest; zero composites nothing
    lb.state.echoes = 2
    assert [round(age * REF_HZ) for _, age in lb.layers()] == [2, 1]
    lb.state.echoes = 0
    assert lb.layers() == []
    rig.release()


def _trail(ctx, hz: float, seconds: float, **dream):
    """(ages, weights) of the echoes after `seconds` drawn at `hz` on the
    renderer's own clock, as the app's frame loop does."""
    rig = Rig(ctx, 200, 128, dream=DreamState(on=True, res=0, **dream))
    n = round(seconds * hz)
    for k in range(1, n + 1):
        rig.frame(t=k / hz)
    ages = [age for _, age in rig.lb.layers()]
    weights = [w for _, w in rig.lb.weights()]
    rig.release()
    return ages, weights


def test_the_same_preset_gives_the_same_trail_at_60_and_120_hz(ctx):
    """Plan 14 WP6: echo time is seconds. TRACER's set (24 echoes every
    1/15 s, a 0.76 s half-life) keeps the same trail on a 120 Hz screen as
    on a 60 Hz one — the same echoes, as old, as bright — where the old
    per-frame decay and cadence halved it."""
    set_ = {"echoes": 24, "gap": 4 / REF_HZ, "fade": fade_of_decay(0.985), "echo_mix": 0.7}
    a60, w60 = _trail(ctx, 60.0, 3.0, **set_)
    a120, w120 = _trail(ctx, 120.0, 3.0, **set_)
    assert len(a60) == len(a120) == 24
    assert a60 == pytest.approx(a120, abs=1.01 / 60)            # within a 60 Hz frame
    assert max(a60) == pytest.approx(1.6, abs=1 / 15)           # 24 × 1/15 s back
    assert sum(w60) == pytest.approx(sum(w120), rel=0.05)
    assert w60[0] == pytest.approx(0.7 * 0.985 ** round(a60[0] * 60), rel=1e-2)
    # the trail 120 Hz used to get: 24 echoes every 4 frames, 0.985 a frame
    old_reach = 24 * 4 / 120.0
    assert max(a120) > 1.9 * old_reach


def test_old_per_frame_values_look_the_same_at_60_hz(ctx):
    """The migration (lookback.migrate_values): WAKE's old 16 echoes every
    2 frames at 0.93 a frame, read as 60 Hz frames, composite exactly the
    weights they did — echo_mix · 0.93^age in frames, an echo every 2nd."""
    from hyperspace.lookback import migrate_values

    vals, notes = migrate_values({"dream.echoes": 16, "dream.decay": 0.93, "dream.every": 2})
    assert set(vals) == {"dream.echoes", "dream.fade", "dream.gap"} and len(notes) == 2
    ages, weights = _trail(ctx, 60.0, 1.0, echoes=16, fade=vals["dream.fade"],
                           gap=vals["dream.gap"], echo_mix=0.3)
    frames = [round(a * 60) for a in ages]
    assert frames == list(range(31, 0, -2))                     # every 2nd frame, 16 of them
    assert weights == pytest.approx([0.3 * 0.93 ** f for f in frames], rel=2e-3)
    # a new id already named wins; nothing to convert is the dict itself
    assert migrate_values({"dream.decay": 0.5, "dream.fade": 1.0})[0] == {"dream.fade": 1.0}
    same = {"dream.fade": 1.0}
    assert migrate_values(same)[0] is same


def test_the_echo_clock_counts_a_frozen_time_as_a_60_hz_frame(ctx):
    """A tool or test drawing at one fixed time sees the old frames: each
    tick that does not move forward is 1/60 s."""
    lb = Lookback(ctx, DreamState())
    for _ in range(3):
        lb.tick(0.0)
    assert lb.clock == pytest.approx(3 / REF_HZ)
    lb.tick(1.0)
    assert lb.clock == pytest.approx(3 / REF_HZ + 1.0)
    lb.release_ring()


def test_capture_cadence(ctx):
    rig = Rig(ctx, 200, 128, dream=DreamState(on=True, echoes=8, gap=3 / REF_HZ, res=0))
    for _ in range(9):
        rig.frame()
    # captures land on frames 3, 6, 9 → ages 7, 4, 1 against frame 10
    assert [round(age * REF_HZ) for _, age in rig.lb.layers()] == [7, 4, 1]
    rig.release()


def test_off_forgets_the_history(ctx):
    rig = Rig(ctx, 200, 128, dream=DreamState(on=True, echoes=4, gap=0.0, res=0))
    for _ in range(4):
        rig.frame()
    assert len(rig.lb.layers()) == 4
    rig.lb.state.on = False
    rig.frame()
    assert rig.lb.layers() == []
    rig.lb.state.on = True
    rig.frame()
    assert [round(age * REF_HZ) for _, age in rig.lb.layers()] == [1]
    rig.release()


def test_res_rebuilds_the_atlas(ctx):
    rig = Rig(ctx, 400, 256, dream=DreamState(on=True, echoes=4, gap=0.0, res=0))
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
    rig = Rig(ctx, w, h, dream=DreamState(on=True, echoes=3, gap=0.0, res=0,
                                          echo_mix=0.7, fade=fade_of_decay(0.8), darken=0.25,
                                          contrast=1.6,
                                          mix=0.5))
    rig.frame()                        # builds the ring; one real capture in slot 0
    lb = rig.lb
    assert lb.echo == (w, h)
    imgs = [synthetic(h, w, k) for k in range(3)]
    lb.clock = 10 / REF_HZ             # slot 0's capture (frame 1) falls off the ring
    lb.frame = 10
    now = lb.now()
    for k, img in enumerate(imgs):     # slots 1..3 hold frames aged 3, 2, 1
        lb.write_slot(k + 1, img, at=now - (3 - k) / REF_HZ)
    assert [round(age * REF_HZ) for _, age in lb.layers()] == [3, 2, 1]
    dream = synthetic(h, w, 9)
    lb.write_from(dream, frame_index=lb.frame)
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
    state = DreamState(on=True, echoes=0, gap=0.0, res=0, darken=0.2, contrast=1.3, mix=0.6,
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
    d = DreamState(on=True, echoes=0, gap=0.0, res=0, darken=0.0, contrast=1.0, mix=1.0,
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
    d = DreamState(on=True, echoes=0, gap=0.0, res=0, mix=1.0, darken=0.0, occlude=1.0)
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
    d = DreamState(on=True, echoes=0, gap=0.0, res=0, darken=0.0, contrast=1.0, mix=1.0)
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
    d = DreamState(on=True, echoes=1, gap=0.0, res=0, darken=0.0, contrast=1.0, mix=0.0,
                   echo_mix=1.0, fade=FADE_HI, tint=1.0, tint_hue=120.0, tint_sat=1.0)
    rig = Rig(ctx, w, h, dream=d)
    rig.frame()
    red = np.zeros((h, w, 4), dtype=np.uint8)
    red[..., 0] = red[..., 3] = 255
    rig.lb.write_slot(0, red, at=rig.lb.clock)
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
    d = DreamState(on=True, echoes=2, gap=3 / REF_HZ, res=0, tint_from=1)
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
    rig = Rig(ctx, 200, 128, dream=DreamState(on=True, echoes=0, gap=0.0, res=0))
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
              dream=DreamState(on=True, echoes=6, gap=0.0, res=0, echo_mix=0.8, fade=fade_of_decay(0.9),
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
    """The app's construction order (tests/test_presets.py `boot`), the
    renderer's own dream and fx states on the registry."""
    from hyperspace import lfo, preset, tempo
    from hyperspace.analysis import Analyser
    from hyperspace.analyzer import Analyzer
    from hyperspace.control import Control
    from hyperspace.library import Library
    from hyperspace.params import build_registry
    from hyperspace.preset import Presets
    from hyperspace.routing import Bindings, Router

    chain = Analyzer(Analyser())
    control = Control(chain)
    view = ViewState()
    r = Renderer(ctx)
    lib = Library(tmp_path, period=0.0)
    reg = build_registry(view, control, SimpleNamespace(chain=chain), lib.project,
                         dream=r.lookback.state, fx=r.fx.state)
    control.library = lib
    clock = tempo.Clock(now=lambda: 0.0)
    tempo.register(reg, clock)
    lfo.register(reg, lfo.LFOs(), clock)
    lib.attach(reg)
    router = Router(reg, Bindings())
    presets = Presets(lib, reg, router)
    preset.migrate_home(lib, router)
    return SimpleNamespace(lib=lib, reg=reg, view=view, r=r, presets=presets)


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


def _factory_presets():
    from hyperspace.library import FACTORY
    return sorted(p.stem for p in (FACTORY / "presets").glob("*.json"))


# every effect on at its own blend, then every one forced to multiply
# (a × b drops alpha wherever an effect returns less than 1)
STRESS = ["effects", "multiply"]


@pytest.mark.parametrize("name", _factory_presets() + STRESS)
def test_every_factory_preset_renders_opaque_in_window_mode(ctx, tmp_path, name):
    """Plan 14 WP1: the render window is a Pepper's Ghost screen — in window
    mode (and fullscreen, the same opaque ground) every pixel of the final
    frame is alpha 255 for every factory preset, and for a preset with
    cut-through, faces, points, the look-back and every effect on, through
    the FX chain and the look-back composite."""
    b = _preset_rig(ctx, tmp_path)
    first = _factory_presets()[0] if name in STRESS else name
    path = b.lib.path_of("presets", first)
    assert path is not None, first
    b.presets.load(json.loads(path.read_text())["name"])
    assert b.lib.current("presets") is not None
    if name in STRESS:
        values = {"view.faces": True, "view.cut_through": True, "view.lines": True,
                  "view.points": True, "fx.on": True, "fx.mix": 1.0, "dream.on": True,
                  "dream.echoes": 6, "dream.gap": 0.0}
        for fx_name in b.r.fx.state.specs:
            values[f"fx.{fx_name}.on"] = True
            values[f"fx.{fx_name}.mix"] = 1.0
        assert b.reg.restore(values) == []
        if name == "multiply":
            for fx_name in b.r.fx.state.specs:
                b.reg[f"fx.{fx_name}.blend"].set(3)
    a = _final_alpha(ctx, b, Output(None, None).bg_alpha)
    assert (a == 255).all(), f"{name}: {(a < 255).mean():.1%} below 255, lowest {a.min()}"
    if name in STRESS:
        assert b.r.fx.active() and b.view.cut_through and b.view.faces


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


def test_a_broken_common_glsl_leaves_the_post_pass_on_the_shipped_helpers(ctx, tmp_path, monkeypatch):
    """audit V2 follow-up: the post pass runs every frame, so a bad edit to
    _common.glsl falls back to the copy as shipped and says so; a fixed
    file lands on the next rebuild."""
    from hyperspace import glsl

    bad = tmp_path / "_common.glsl"
    bad.write_text("this is not glsl\n")
    monkeypatch.setattr(glsl, "COMMON_GLSL", bad)
    lb = Lookback(ctx)
    assert lb.error.startswith("_common.glsl:1:")
    bad.write_text(glsl.FALLBACK)
    lb.on_reload()
    assert lb.error == ""


def test_source_protocol():
    assert isinstance(Echo(), LookbackSource)
    assert not isinstance(object(), LookbackSource)


def test_dream_slot_round_trip(ctx):
    w, h = echo_size(128, 400, 256)
    src = Echo()
    rig = Rig(ctx, w, h, dream=DreamState(on=True, echoes=0, gap=0.0, res=0, mix=1.0,
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
    rig = Rig(ctx, w, h, dream=DreamState(on=True, echoes=1, gap=0.0, res=0))
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
    rig = Rig(ctx, 1280, 820, dream=DreamState(on=True, echoes=1, gap=0.0, res=2))
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
    from hyperspace.analyzer import Analyzer
    from hyperspace.control import Control
    from hyperspace.params import build_registry

    chain = Analyzer(Analyser())
    audio = SimpleNamespace(chain=chain)
    return build_registry(ViewState(), Control(chain), audio, None, dream=dream)


DREAM_IDS = [
    "dream.on", "dream.mix", "dream.echo_mix", "dream.fade", "dream.darken",
    "dream.contrast", "dream.occlude", "dream.hue", "dream.sat", "dream.tint", "dream.tint_from",
    "dream.tint_hue", "dream.tint_sat",
    "dream.echoes", "dream.gap", "dream.res", "dream.steps", "dream.step",
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
    rebuild = ("dream.gap", "dream.res", "dream.layer")
    assert not any(reg[pid].modulatable for pid in rebuild)
    assert all(reg[pid].modulatable for pid in DREAM_IDS if pid not in rebuild)
    assert reg["dream.res"].names == [str(v) for v in RES]
    assert reg["dream.layer"].names[1] == "conv3_3"
    # the params write the state the compositor reads
    reg["dream.on"].set(True)
    reg["dream.echoes"].set_value(8)
    reg["dream.res"].set(3)
    assert d.on and d.echoes == 8 and d.res == 3
    # a fresh state stands in when no renderer is passed
    assert "dream.k" in registry()


def test_a_route_on_the_dream_layer_is_dormant():
    """Plan 16 WP5: `dream.layer` is not a performer's — a change makes the
    worker load another trunk. A route onto it does nothing, quietly; a
    scene-setter (the panel, a preset, a key or desk row) still sets it."""
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
    # the scene-setters: the panel's write, a preset's restore, a key row
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
        reg = build_registry(view, control, audio, lib.project, dream=d)
        lib.attach(reg)
        # no renderer: the thumbnail row says so instead of drawing textures
        panel = Panel(control, audio, view, bank=lib.project, registry=reg, library=lib)
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
    ("dream.echo_mix", "CONTINUOUS", 0.0, 1.0, 0.4, True, True, False, False, False, None),
    ("dream.fade", "CONTINUOUS", 0.02, 10.0, 0.2252, True, True, False, True, False, None),
    ("dream.darken", "CONTINUOUS", 0.0, 1.0, 0.1, True, True, False, False, False, None),
    ("dream.contrast", "CONTINUOUS", 0.5, 3.0, 1.0, True, True, False, False, False, None),
    ("dream.occlude", "CONTINUOUS", 0.0, 1.0, 1.0, True, True, False, False, False, None),
    ("dream.hue", "CONTINUOUS", -180.0, 180.0, 0.0, True, True, False, False, True, None),
    ("dream.sat", "CONTINUOUS", 0.0, 2.0, 1.0, True, True, False, False, False, None),
    ("dream.tint", "CONTINUOUS", 0.0, 1.0, 0.0, True, True, False, False, False, None),
    ("dream.tint_from", "ENUM", 0.0, 1.0, 0, True, True, False, False, False,
     ("colour", "scene")),
    ("dream.tint_hue", "CONTINUOUS", 0.0, 360.0, 200.0, True, True, False, False, True, None),
    ("dream.tint_sat", "CONTINUOUS", 0.0, 1.0, 1.0, True, True, False, False, False, None),
    ("dream.echoes", "CONTINUOUS", 0, 32, 8, True, True, True, False, False, None),
    ("dream.gap", "CONTINUOUS", 0.0, 0.25, 0.033333, True, False, False, False, False, None),
    ("dream.res", "ENUM", 0.0, 1.0, 2, True, False, False, False, False,
     ("128", "192", "256", "384")),
    ("dream.steps", "CONTINUOUS", 1, 3, 2, True, True, True, False, False, None),
    ("dream.step", "CONTINUOUS", 0.005, 0.06, 0.03, True, True, False, False, False, None),
    ("dream.k", "CONTINUOUS", 0.03, 0.3, 0.05, True, True, False, False, False, None),
    ("dream.layer", "ENUM", 0.0, 1.0, 1, True, False, False, False, False,
     ("conv2_2", "conv3_3", "conv4_3", "inception3b", "inception4c", "inception4e")),
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
        self.reg = build_registry(view, control, audio, lib.project, dream=self.dream)
        lib.attach(self.reg)
        self.panel = ui.Panel(control, audio, view, bank=lib.project, registry=self.reg,
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
                   "invisible_button", "color_button"):
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


def test_the_page_has_three_sections_and_every_dream_param_once(lbpage):
    """ECHOES, DREAM, BOTH, in that order under the page's own title, and
    every persisted `dream.*` param drawn exactly once, under the section
    that says what it acts on (plan 20 §1, "The look-back page's knobs
    today")."""
    from hyperspace import ui_lookback

    lbpage.frame()
    got = lbpage.by_section()
    assert list(got) == ["look-back", "echoes", "dream", "both"]
    assert got["look-back"] == ["dream.on"]
    assert got["echoes"] == ["dream.echo_mix", "dream.fade", "dream.echoes", "dream.gap"]
    assert set(got["dream"]) == {
        "dream.layer", "dream.mix", "dream.k", "dream.step", "dream.steps", "dream.mask_decay",
        "dream.jitter", "dream.octaves", "dream.hue", "dream.sat", "dream.tint",
        "dream.tint_from", "dream.tint_hue", "dream.tint_sat"}
    assert got["both"] == ["dream.darken", "dream.contrast", "dream.occlude", "dream.res"]
    # the layout table is what was drawn, and it is the whole group, once
    assert {k: tuple(v) for k, v in got.items() if k != "look-back"} == ui_lookback.SECTIONS
    drawn = [pid for ids in got.values() for pid in ids]
    assert sorted(drawn) == sorted(DREAM_IDS)
    # one widget per param (the layer: one chip per choice), on or off
    for on in (False, True):
        lbpage.dream.on = on
        lbpage.frame()
        ids = [w for w in lbpage.widgets() if "dream." in w]
        chips = [w for w in ids if w.startswith("chip.dream.layer.")]
        assert len(chips) == 6 and len(ids) - len(chips) == len(DREAM_IDS) - 1
        assert sorted(set(ids) - set(chips)) == sorted(set(DREAM_IDS) - {"dream.layer"})
    # every cell has a label, and every label is in the page's table
    labels = [text for kind, text in lbpage.events if kind == "label"]
    cells = [pid for title in ("echoes", "dream", "both") for pid in ui_lookback.SECTIONS[title]
             if pid != "dream.layer"]
    assert [lb for lb in labels if lb != "the tint"] == [ui_lookback.SHORT[pid] for pid in cells]


def test_the_layer_is_a_row_of_chips(lbpage):
    """`dream.layer` is six chips, one per `lookback.LAYERS` entry in order,
    the lit one the layer's base; a click sets it (a scene-setter's write:
    the param is not modulatable); there is no combo for it; and each chip
    opens the param's own menu on a right-click, one popup apiece."""
    from hyperspace import ui_lookback
    from hyperspace.lookback import LAYERS

    reg, d = lbpage.reg, lbpage.dream
    layer = reg["dream.layer"]
    assert len(LAYERS) == 6 and list(ui_lookback.LAYER_CHIPS) == LAYERS
    assert len(set(ui_lookback.LAYER_CHIPS.values())) == 6
    lbpage.frame()
    chips = [f"chip.dream.layer.{k}" for k in range(6)]
    assert [w for w in lbpage.widgets() if w.startswith("chip.dream.layer")] == chips
    assert "dream.layer" not in lbpage.widgets()                 # no combo
    assert [lbpage.lit[c] for c in chips] == [k == 1 for k in range(6)]    # conv3_3, the default
    # one row, tiling it: equal widths, left to right, the same line
    rects = [lbpage.rects[c] for c in chips]
    assert len({round(r[1]) for r in rects}) == 1
    assert [r[0] for r in rects] == sorted(r[0] for r in rects)
    widths = [r[2] - r[0] for r in rects]
    assert max(widths) - min(widths) < 1.0
    assert all(rects[k][2] <= rects[k + 1][0] for k in range(5))  # none overlaps the next
    # a click on each selects it, and it alone is lit
    for k in (4, 0, 5, 2):
        lbpage.click(chips[k])
        assert layer.base == k and d.layer == k
        assert [lbpage.lit[c] for c in chips] == [j == k for j in range(6)]
    assert not layer.modulatable and not layer.modulated
    # a click on the lit one keeps it (a chip is a choice, not a toggle)
    lbpage.click(chips[2])
    assert d.layer == 2
    # the param's menu hangs off every chip, a popup apiece
    popups = [text for kind, text in lbpage.events if kind == "popup"]
    assert [p for p in popups if "dream.layer" in p] == [f"##ctx.dream.layer.{k}" for k in range(6)]
    lbpage.click(chips[3], button=1)                # a right-click opens the menu, sets nothing
    assert d.layer == 2
    assert lbpage.imgui.is_popup_open("", lbpage.imgui.PopupFlags_.any_popup_id)


def test_an_armed_learn_outlines_the_chip_row_once(lbpage, monkeypatch):
    """Six chips stand for one param: armed to learn, the row gets one
    outline (as the combo it replaces had), not one per chip."""
    from hyperspace import ui

    framed: list[str] = []
    real = ui.Panel._learn_frame
    monkeypatch.setattr(ui.Panel, "_learn_frame",
                        lambda self, p: (framed.append(p.id), real(self, p))[1])
    lbpage.panel.learn = SimpleNamespace(learning="dream.layer", arm=lambda pid: None)
    lbpage.frame()
    assert "dream.layer" not in framed and "dream.mix" in framed
    assert [w for w in lbpage.widgets() if w.startswith("chip.dream.layer")] == [
        f"chip.dream.layer.{k}" for k in range(6)]


def test_spacing_is_called_time_apart(lbpage):
    """The owner's "Spacing does not say what it is": the page's cell says
    TIME APART, the registry (so ROUTING, Learn and the desk diagram) says
    "Echo time apart", the readout is a time, and the tip opens with what
    it is. Echo time is seconds: the fade is a time too."""
    from hyperspace import ui_lookback

    reg = lbpage.reg
    gap, fade = reg["dream.gap"], reg["dream.fade"]
    assert ui_lookback.SHORT["dream.gap"] == "time apart"
    assert gap.label == "Echo time apart"
    assert gap.tip.startswith("The time between one echo and the next")
    assert gap.text() == "33 ms" and not gap.modulatable
    assert fade.label == "Echo fade time" and ui_lookback.SHORT["dream.fade"] == "fade time"
    assert fade.text() == "0.23 s" and "halves in brightness every" in fade.tip
    lbpage.frame()
    events = lbpage.events
    k = events.index(("label", "time apart"))
    assert events[k + 1] == ("widget", "dream.gap")           # the label is that slider's
    assert not [text for kind, text in events if kind == "label" and "spacing" in text.lower()]
    # no label on the page or in the group says the old word
    assert not [p.id for p in reg.group("dream") if "spacing" in (p.label + p.tip).lower()]
    # the section's note says the trail in the same units
    assert ui_lookback._trail_note(reg) == "8 × 33 ms · the trail reaches 0.27 s"
    gap.set_value(0.0)
    assert ui_lookback._trail_note(reg) == "8, one a frame"
    reg["dream.echoes"].set_value(0)                # a supported value: the dream alone
    assert ui_lookback._trail_note(reg) == "no echoes: the dream alone"


def test_every_dream_label_says_whose_knob_it_is():
    """Fork F9: the registry's labels change with the page's. An echo knob
    says Echo, a dream knob says Dream, the three that grade both and the
    switch say neither; every tip opens with a sentence."""
    from hyperspace import ui_lookback

    reg = registry()
    for pid in ui_lookback.SECTIONS["echoes"]:
        assert reg[pid].label.startswith("Echo "), pid
    for pid in ui_lookback.SECTIONS["dream"]:
        assert reg[pid].label.startswith("Dream "), pid
    assert [reg[pid].label for pid in ui_lookback.SECTIONS["both"]] == [
        "Darken", "Contrast", "Shape hides wake", "Look-back detail"]
    assert reg["dream.on"].label == "Look-back"
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
    """ROUTING's target list is the registry's labels: it says "Echo
    brightness" and "Dream brightness" where it said "Echo mix" and "Dream
    mix", and a search for the page's word finds the param."""
    from hyperspace import ui_routing

    reg = registry()
    targets = {p.id: p.label for p in ui_routing._targets(SimpleNamespace(reg=reg))
               if p.id.startswith("dream.")}
    assert targets["dream.echo_mix"] == "Echo brightness"
    assert targets["dream.mix"] == "Dream brightness"
    assert targets["dream.fade"] == "Echo fade time"
    assert targets["dream.echoes"] == "Echo count"
    assert targets["dream.occlude"] == "Shape hides wake"
    assert targets["dream.step"] == "Dream strength"
    assert targets["dream.mask_decay"] == "Dream linger"
    old = {"Echo mix", "Dream mix", "Fade", "Echoes", "Spacing", "Occlude", "Hue shift",
           "Saturation", "Tint", "Step size", "Steps", "Mask decay", "Jitter", "Octaves",
           "Layer", "Resolution"}
    assert not old & set(targets.values())
    # the three that rebuild things are still not a performer's
    assert not set(targets) & {"dream.gap", "dream.res", "dream.layer"}


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
    cells = [w for w in lbpage.by_section()["dream"] if w != "dream.layer"]
    assert cells[:2] == ["dream.mix", "dream.k"]
    mix, speed = lbpage.rects["dream.mix"], lbpage.rects["dream.k"]
    assert round(mix[1]) == round(speed[1]) and mix[2] < speed[0]
    # right is faster: the slider's value is k itself, and it writes the state
    k.set_value(0.2)
    assert lbpage.dream.k == pytest.approx(0.2)
    # ROUTING lists it under the new name; a preset still carries the old id
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
    for value, reads in ((0.05, "≈14 frames"), (0.3, "≈2 frames"), (0.03, "≈23 frames"),
                         (0.04, "≈17 frames"), (0.1, "≈7 frames")):
        k.set_value(value)
        assert k.text() == reads, value
        assert k.fmt(value) == reads
    assert (k.fmt(k.lo), k.fmt(k.hi)) == ("≈23 frames", "≈2 frames")
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
    # the speed's readout fits its half-width cell like the others
    assert max(len(k.fmt(v)) for v in (k.lo, k.hi, 0.05)) <= 10


def test_the_look_back_page_has_no_conflicting_ids(lbpage):
    """Every widget on the page has its own imgui id and its own popup:
    six chips stand for one param, and two cells are both called
    BRIGHTNESS."""
    for on in (False, True):
        lbpage.dream.on = on
        lbpage.frame()
        ids = lbpage.widgets()
        assert not {i for i in ids if ids.count(i) > 1}
        popups = [text for kind, text in lbpage.events if kind == "popup"]
        assert not {i for i in popups if popups.count(i) > 1}
        # every dream.* widget offers its param's menu
        assert {p[len("##ctx."):] for p in popups} >= set(DREAM_IDS) - {"dream.layer"}


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


def test_the_relabel_changes_no_factory_file(tmp_path):
    """Labels are not in preset files: the factory presets regenerate to
    the bytes they have, and the dream module presets name ids only."""
    import shutil

    from hyperspace import preset
    from hyperspace.library import Library

    for path in preset.FACTORY_DIR.glob("*.json"):
        shutil.copy(path, tmp_path / path.name)
    preset.write_factory(tmp_path)
    for path in preset.FACTORY_DIR.glob("*.json"):
        assert (tmp_path / path.name).read_bytes() == path.read_bytes(), path.name
    reg = registry()
    lib = Library(tmp_path / "home", period=0.0)
    lib.attach(reg)
    for name in lib.list("dream"):
        assert set(lib.read("dream", name)["values"]) <= set(DREAM_IDS), name


# ---------------------------------------------------------------- plan 14 WP1: the freeze

def test_capture_off_the_cadence_with_no_source_puts_the_target_back(ctx):
    """The early return (not a commit frame, no worker, no scene tint) left
    the atlas `_ensure` had bound; every return now binds `target`."""
    rig = Rig(ctx, 200, 128, dream=DreamState(on=True, echoes=4, gap=2 / REF_HZ, res=0))
    rig.lb.source = None
    scene = ctx.texture((200, 128), 4)
    rig.fbo.use()
    rig.lb.capture(scene, rig.fbo)            # frame 1: off the cadence
    assert rig.lb.frame == 1 and rig.lb._captures == []
    assert ctx.fbo is rig.fbo
    rig.lb.capture(scene, rig.fbo)            # frame 2: a commit
    assert ctx.fbo is rig.fbo and len(rig.lb._captures) == 1
    scene.release()
    rig.release()


def test_the_atlas_fits_the_drivers_largest_texture(ctx, monkeypatch):
    """A portrait window at res 384 asked for a 36 864 px tall atlas, past
    GL_MAX_TEXTURE_SIZE, and capture raised every frame. The slot shrinks,
    aspect kept, so the atlas fits; when the textures cannot be made at
    all, nothing is captured and the reason is on `ring_error`."""
    from hyperspace.lookback import fit_atlas

    assert fit_atlas((384, 1152), 16384) == (168, 512)
    assert fit_atlas((400, 256), 16384) == (400, 256)
    ew, eh = fit_atlas(echo_size(RES[-1], 820, 2460), 16384)
    assert eh * MAX_ECHOES <= 16384 and ew <= 16384
    lb = Lookback(ctx, DreamState(on=True, echoes=4, gap=0.0, res=len(RES) - 1))
    monkeypatch.setattr(lb, "max_texture", lambda: 4096)
    tex = ctx.texture((120, 360), 4)
    fbo = ctx.framebuffer(color_attachments=[tex])
    fbo.use()
    lb.capture(tex, fbo)
    assert lb.atlas is not None and lb.atlas.size[1] <= 4096 and lb.ring_error == ""
    assert len(lb._captures) == 1 and ctx.fbo is fbo
    # the driver refuses outright: no history, no echo recorded, no raise
    lb.release_ring()
    lb._captures.clear()
    real = ctx.texture

    def refuse(size, *a, **k):
        if size[1] > 1000:
            raise moderngl.Error("GL_INVALID_VALUE")
        return real(size, *a, **k)

    monkeypatch.setattr(lb, "ctx", SimpleNamespace(texture=refuse, framebuffer=ctx.framebuffer,
                                                   clear=ctx.clear, info=ctx.info))
    monkeypatch.setattr(lb, "max_texture", lambda: 1 << 20)
    frame = lb.frame
    lb.capture(tex, fbo)
    assert lb.atlas is None and lb._captures == [] and lb.frame == frame
    assert lb.ring_error.startswith("look-back: no history at ")
    assert ctx.fbo is fbo
    fbo.release()
    tex.release()
